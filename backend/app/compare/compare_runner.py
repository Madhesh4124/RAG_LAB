import asyncio
import os
import re
import threading
import time
import uuid
from typing import Any, List, Tuple


from app.compare.collection_registry import get_or_load_collection
from app.compare.utils import calc_avg_similarity, filter_by_threshold, derive_config_signature
from app.compare.schemas import ConfigResult, RAGConfig
from app.services.chunking.base import Chunk
from app.services.evaluation.retrieval_metrics import build_retrieval_metrics_report
from app.services.query_classifier import classify_query
from app.services.summary_service import SummaryService
from app.compare.summary_store import get_summary as get_compare_summary, upsert_summary as upsert_compare_summary
from sqlalchemy.ext.asyncio import AsyncSession


_LLM_CACHE: dict[tuple, Any] = {}
_LLM_CACHE_LOCK = threading.Lock()


def _clean_answer_text(text: str) -> str:
    """Strip internal thought traces, thinking process blocks, and preambles from model output."""
    cleaned = str(text or "").strip()
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", cleaned, flags=re.IGNORECASE).strip()
    if "Here's a thinking process:" in cleaned or "Here is a thinking process:" in cleaned:
        m = re.search(
            r"(?:(?:Therefore|In summary|In conclusion|To answer your question|Final Answer:?|Answer:?|Conclusion:?)\s*[:\n]+)([\s\S]+)$",
            cleaned,
            re.IGNORECASE,
        )
        if m and len(m.group(1).strip()) > 10:
            return m.group(1).strip()
        sections = re.split(r"\n\s*(?:---\s*\n|\*{3,}\s*\n|\b(?:Final Answer|Answer)\b:?)", cleaned, flags=re.IGNORECASE)
        if len(sections) > 1 and len(sections[-1].strip()) > 10:
            return sections[-1].strip()
        paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
        if paragraphs:
            last_p = paragraphs[-1]
            if not last_p.lower().startswith(("here's a thinking", "1.", "2.", "3.", "4.", "5.", "- ", "* ")):
                return last_p
    return cleaned


def _get_cached_compare_llm(model: str = "nvidia/nemotron-3.5-lightning-30b-a3b", api_key: str | None = None) -> Any:
    # 1. Primary: NVIDIA NIM (nemotron-3.5-lightning-30b-a3b)
    nvidia_api_key = api_key or os.getenv("NVIDIA_API_KEY")
    if nvidia_api_key:
        cache_key = ("nvidia", model, nvidia_api_key)
        with _LLM_CACHE_LOCK:
            cached = _LLM_CACHE.get(cache_key)
        if cached is not None:
            return cached
        try:
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            llm = ChatNVIDIA(
                model=model,
                api_key=nvidia_api_key,
                temperature=0.2,
                max_completion_tokens=2048,
                model_kwargs={"chat_template_kwargs": {"enable_thinking": False}},
            )
            with _LLM_CACHE_LOCK:
                _LLM_CACHE.setdefault(cache_key, llm)
                return _LLM_CACHE[cache_key]
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("ChatNVIDIA initialization failed (%s); trying Groq", exc)

    # 2. Fallback: Groq (openai/gpt-oss-120b)
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        fallback_model = "openai/gpt-oss-120b"
        cache_key = ("groq", fallback_model, groq_api_key)
        with _LLM_CACHE_LOCK:
            cached = _LLM_CACHE.get(cache_key)
        if cached is not None:
            return cached
        try:
            from langchain_groq import ChatGroq
            llm = ChatGroq(
                model=fallback_model,
                temperature=0.0,
                api_key=groq_api_key,
                max_tokens=2048,
                max_retries=1,
            )
            with _LLM_CACHE_LOCK:
                _LLM_CACHE.setdefault(cache_key, llm)
                return _LLM_CACHE[cache_key]
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("ChatGroq initialization failed: %s", exc)

    raise ValueError("Neither NVIDIA_API_KEY nor GROQ_API_KEY is available for compare generation.")


def _to_similarity(score: float) -> float:
    # Chroma commonly returns distance, where lower is better.
    if score < 0:
        return float(score)
    if score <= 1.0:
        return max(0.0, min(1.0, 1.0 - score))
    return max(0.0, min(1.0, 1.0 / (1.0 + score)))


def _extract_text(doc_obj) -> str:
    if hasattr(doc_obj, "page_content"):
        return str(doc_obj.page_content)
    if hasattr(doc_obj, "text"):
        return str(doc_obj.text)
    return str(doc_obj)


class _LLMWrapper:
    def __init__(self, llm):
        self.llm = llm


async def _summarize_compare_context(
    query: str,
    config: RAGConfig,
    vectorstore,
    llm,
    user_scope: str | None,
    db: AsyncSession | None = None,
) -> tuple[str | None, List[Tuple], List[str]]:
    summary_key = derive_config_signature(config, user_scope=user_scope)
    if db is not None and user_scope is not None:
        cached_summary = await get_compare_summary(
            db=db,
            user_id=uuid.UUID(user_scope),
            config_signature=summary_key,
        )
        if cached_summary:
            return cached_summary, [], []

    summary_query = "document summary main idea key takeaways"
    raw_results = await asyncio.to_thread(
        vectorstore.similarity_search_with_score,
        summary_query,
        max(config.top_k, 30),
    )
    fallback_results: List[Tuple] = [
        (doc, _to_similarity(float(score))) for doc, score in raw_results
    ]
    fallback_results = filter_by_threshold(fallback_results, config.threshold)
    if not fallback_results and raw_results:
        fallback_results = [
            (doc, _to_similarity(float(score))) for doc, score in raw_results[: max(config.top_k, 30)]
        ]

    fallback_chunks = [
        Chunk(text=_extract_text(doc), metadata={})
        for doc, _ in fallback_results
        if _extract_text(doc).strip()
    ]
    summary = await SummaryService.generate_doc_summary(fallback_chunks, _LLMWrapper(llm)) if fallback_chunks else None
    if summary and db is not None and user_scope is not None:
        await upsert_compare_summary(
            db=db,
            user_id=uuid.UUID(user_scope),
            config_signature=summary_key,
            summary=summary,
        )
    return summary, fallback_results, fallback_chunks


async def run_single_config(
    query: str,
    config: RAGConfig,
    user_scope: str | None = None,
    db: AsyncSession | None = None,
    include_evaluation: bool = False,
) -> ConfigResult:
    start = time.perf_counter()

    query_mode = classify_query(query)

    vectorstore = get_or_load_collection(
        config.collection_name,
        config.embedding_provider,
        config.embedding_model,
        user_scope=user_scope,
    )

    llm = _get_cached_compare_llm()

    if query_mode == "global":
        summary, fallback_results, fallback_chunks = await _summarize_compare_context(
            query=query,
            config=config,
            vectorstore=vectorstore,
            llm=llm,
            user_scope=user_scope,
            db=db,
        )

        answer = summary or "No document summary could be generated from the indexed context."
        chunks = [_extract_text(doc) for doc, _ in fallback_results] if fallback_results else []
        scores = [round(float(score), 4) for _, score in fallback_results]
        end = time.perf_counter()
        latency_ms = (end - start) * 1000.0

        chunk_details = [
            {
                "index": idx + 1,
                "text": _extract_text(doc),
                "score": scores[idx] if idx < len(scores) else 0.0,
                "page_number": getattr(doc, "metadata", {}).get("page_number")
                or getattr(doc, "metadata", {}).get("page")
                or None,
                "filename": getattr(doc, "metadata", {}).get("filename", None),
                "chunk_strategy": getattr(doc, "metadata", {}).get("chunk_strategy", config.chunk_strategy),
            }
            for idx, (doc, _) in enumerate(fallback_results)
        ]

        retrieved_items = [
            {"text": chunk_text, "score": scores[idx] if idx < len(scores) else 0.0}
            for idx, chunk_text in enumerate(chunks)
        ]
        candidate_items = [
            {"text": _extract_text(doc), "score": float(score)}
            for doc, score in fallback_results
        ]

        global_eval = None
        try:
            from app.services.evaluation.retrieval_metrics import unified_deep_evaluation, _get_evaluator_llm
            eval_llm = _get_evaluator_llm(_LLMWrapper(llm))
            unified_res = None
            if eval_llm and chunks:
                try:
                    unified_res = await asyncio.to_thread(
                        unified_deep_evaluation,
                        query=query,
                        answer=answer,
                        retrieved_chunks=retrieved_items,
                        candidate_chunks=candidate_items,
                        llm_client=_LLMWrapper(eval_llm),
                    )
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning("Compare global unified evaluation skipped: %s", e)

            global_eval = build_retrieval_metrics_report(
                query=query,
                answer=answer,
                retrieved_chunks=retrieved_items,
                candidate_chunks=candidate_items,
                llm_client=_LLMWrapper(eval_llm or llm),
                retrieval_config={
                    "type": "compare",
                    "top_k": config.top_k,
                    "similarity_threshold": config.threshold,
                },
                query_mode="global",
                precomputed_retrieved_flags=unified_res.get("retrieved_flags") if unified_res else None,
                precomputed_candidate_flags=unified_res.get("candidate_flags") if unified_res else None,
            )
            if unified_res:
                for key in ("faithfulness", "answer_relevancy", "context_recall"):
                    if unified_res.get(key) is not None:
                        global_eval.setdefault("answer_metrics", {})[key] = unified_res[key]
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("Failed building global compare evaluation: %s", exc)

        return ConfigResult(
            config=config,
            answer=answer,
            chunks=chunks,
            scores=scores,
            latency_ms=round(latency_ms, 3),
            avg_similarity=calc_avg_similarity(scores),
            chunk_count=len(chunks),
            evaluation=global_eval,
            chunk_details=chunk_details,
        )

    raw_results = await asyncio.to_thread(
        vectorstore.similarity_search_with_score,
        query,
        config.top_k,
    )

    normalized_results: List[Tuple] = [
        (doc, _to_similarity(float(score))) for doc, score in raw_results
    ]
    filtered_results = filter_by_threshold(normalized_results, config.threshold)

    # If thresholding removes everything, keep top retrieved chunks so the
    # comparison still has context to answer from.
    if not filtered_results and normalized_results:
        filtered_results = sorted(normalized_results, key=lambda item: float(item[1]), reverse=True)[: config.top_k]

    chunks = [_extract_text(doc) for doc, _ in filtered_results]
    scores = [round(float(score), 4) for _, score in filtered_results]

    compacted_context = []
    total_chars = 0
    for c in chunks:
        txt = c[:2000] + "..." if len(c) > 2000 else c
        if total_chars + len(txt) > 10000 and compacted_context:
            break
        compacted_context.append(txt)
        total_chars += len(txt)
    context = "\n\n---\n\n".join(compacted_context) if compacted_context else "No relevant context retrieved."
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert research assistant. Answer the user question based directly on the provided context.\n"
                "CRITICAL: Do NOT output internal thoughts, reasoning steps, or 'Here's a thinking process'. "
                "Output ONLY the final, direct answer concisely."
            ),
        },
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer based only on the context provided.",
        },
    ]

    try:
        llm_response = await asyncio.to_thread(llm.invoke, messages)
        raw_ans = str(getattr(llm_response, "content", "")).strip()
        answer = _clean_answer_text(raw_ans)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Primary compare generation failed (%s); trying Groq fallback", exc)
        try:
            groq_key = os.getenv("GROQ_API_KEY")
            if groq_key:
                from langchain_groq import ChatGroq
                fb_llm = ChatGroq(
                    model="openai/gpt-oss-120b",
                    temperature=0.0,
                    api_key=groq_key,
                    max_tokens=2048,
                    max_retries=1,
                )
                llm_response = await asyncio.to_thread(fb_llm.invoke, messages)
                raw_ans = str(getattr(llm_response, "content", "")).strip()
                answer = _clean_answer_text(raw_ans)
            else:
                raise exc
        except Exception as fb_exc:
            logging.getLogger(__name__).error("Fallback compare generation also failed: %s", fb_exc)
            if chunks:
                answer = "Based on retrieved context:\n\n" + "\n\n".join(chunks[:2])
            else:
                answer = "No relevant context found to answer the query."

    end = time.perf_counter()
    latency_ms = (end - start) * 1000.0

    chunk_details = [
        {
            "index": idx + 1,
            "text": _extract_text(doc),
            "score": scores[idx] if idx < len(scores) else 0.0,
            "page_number": getattr(doc, "metadata", {}).get("page_number")
            or getattr(doc, "metadata", {}).get("page")
            or None,
            "filename": getattr(doc, "metadata", {}).get("filename", None),
            "chunk_strategy": getattr(doc, "metadata", {}).get("chunk_strategy", config.chunk_strategy),
        }
        for idx, (doc, _) in enumerate(filtered_results)
    ]

    retrieved_items = [
        {"text": chunk_text, "score": scores[idx] if idx < len(scores) else 0.0}
        for idx, chunk_text in enumerate(chunks)
    ]
    candidate_items = [
        {"text": _extract_text(doc), "score": float(score)}
        for doc, score in normalized_results
    ]

    evaluation = None
    if include_evaluation:
        try:
            from app.services.evaluation.retrieval_metrics import unified_deep_evaluation, _get_evaluator_llm
            eval_llm = _get_evaluator_llm(_LLMWrapper(llm))
            unified_res = None
            if eval_llm and chunks:
                try:
                    unified_res = await asyncio.to_thread(
                        unified_deep_evaluation,
                        query=query,
                        answer=answer,
                        retrieved_chunks=retrieved_items,
                        candidate_chunks=candidate_items,
                        llm_client=_LLMWrapper(eval_llm),
                    )
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning("Compare unified evaluation skipped: %s", e)

            evaluation = build_retrieval_metrics_report(
                query=query,
                answer=answer,
                retrieved_chunks=retrieved_items,
                candidate_chunks=candidate_items,
                llm_client=_LLMWrapper(eval_llm or llm),
                retrieval_config={
                    "type": "compare",
                    "top_k": config.top_k,
                    "similarity_threshold": config.threshold,
                },
                query_mode="local",
                precomputed_retrieved_flags=unified_res.get("retrieved_flags") if unified_res else None,
                precomputed_candidate_flags=unified_res.get("candidate_flags") if unified_res else None,
            )
            if unified_res:
                for key in ("faithfulness", "answer_relevancy", "context_recall"):
                    if unified_res.get(key) is not None:
                        evaluation.setdefault("answer_metrics", {})[key] = unified_res[key]
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("Failed building compare evaluation: %s", exc)
    else:
        # Instant lexical / mathematical metrics report (0ms, no LLM judge)
        try:
            evaluation = build_retrieval_metrics_report(
                query=query,
                answer=answer,
                retrieved_chunks=retrieved_items,
                candidate_chunks=candidate_items,
                llm_client=None,
                retrieval_config={
                    "type": "compare",
                    "top_k": config.top_k,
                    "similarity_threshold": config.threshold,
                },
                query_mode="local",
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Failed building instant compare metrics: %s", exc)

    return ConfigResult(
        config=config,
        answer=answer,
        chunks=chunks,
        scores=scores,
        latency_ms=round(latency_ms, 3),
        avg_similarity=calc_avg_similarity(scores),
        chunk_count=len(chunks),
        evaluation=evaluation,
        chunk_details=chunk_details,
    )


async def evaluate_single_result(query: str, result: ConfigResult) -> ConfigResult:
    """Run deep LLM evaluation on an existing comparison result on-demand."""
    if not result.chunks:
        return result

    retrieved_items = [
        {"text": c, "score": result.scores[idx] if idx < len(result.scores) else 0.0}
        for idx, c in enumerate(result.chunks)
    ]
    candidate_items = [
        {"text": d.get("text", ""), "score": float(d.get("score", 0.0))}
        for d in (result.chunk_details or [])
    ] if result.chunk_details else retrieved_items

    try:
        from app.services.evaluation.retrieval_metrics import unified_deep_evaluation, _get_evaluator_llm
        llm = _get_cached_compare_llm()
        eval_llm = _get_evaluator_llm(_LLMWrapper(llm))
        unified_res = None
        if eval_llm:
            unified_res = await asyncio.to_thread(
                unified_deep_evaluation,
                query=query,
                answer=result.answer,
                retrieved_chunks=retrieved_items,
                candidate_chunks=candidate_items,
                llm_client=_LLMWrapper(eval_llm),
            )

        evaluation = build_retrieval_metrics_report(
            query=query,
            answer=result.answer,
            retrieved_chunks=retrieved_items,
            candidate_chunks=candidate_items,
            llm_client=_LLMWrapper(eval_llm or llm),
            retrieval_config={
                "type": "compare",
                "top_k": result.config.top_k,
                "similarity_threshold": result.config.threshold,
            },
            query_mode="local",
            precomputed_retrieved_flags=unified_res.get("retrieved_flags") if unified_res else None,
            precomputed_candidate_flags=unified_res.get("candidate_flags") if unified_res else None,
        )
        if unified_res:
            for key in ("faithfulness", "answer_relevancy", "context_recall"):
                if unified_res.get(key) is not None:
                    evaluation.setdefault("answer_metrics", {})[key] = unified_res[key]
        result.evaluation = evaluation
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("On-demand evaluation failed for %s: %s", result.config.name, exc)

    return result


async def evaluate_comparison_results(
    query: str,
    results: List[ConfigResult],
) -> List[ConfigResult]:
    """Concurrently evaluate multiple pipeline results."""
    tasks = [evaluate_single_result(query, r) for r in results]
    updated = await asyncio.gather(*tasks, return_exceptions=False)
    return list(updated)


async def run_comparison(
    query: str,
    configs: List[RAGConfig],
    user_scope: str | None = None,
    db: AsyncSession | None = None,
    include_evaluation: bool = False,
) -> List[ConfigResult]:
    # Run all staged pipeline comparisons concurrently
    tasks = [
        run_single_config(
            query=query,
            config=cfg,
            user_scope=user_scope,
            db=db,
            include_evaluation=include_evaluation,
        )
        for cfg in configs
    ]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    return list(results)
