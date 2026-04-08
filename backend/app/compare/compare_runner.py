import asyncio
import os
import threading
import time
import uuid
from typing import List, Tuple

from langchain_google_genai import ChatGoogleGenerativeAI

from app.compare.collection_registry import get_or_load_collection
from app.compare.utils import calc_avg_similarity, filter_by_threshold, derive_config_signature
from app.compare.schemas import ConfigResult, RAGConfig
from app.services.chunking.base import Chunk
from app.services.query_classifier import classify_query
from app.services.summary_service import SummaryService
from app.compare.summary_store import get_summary as get_compare_summary, upsert_summary as upsert_compare_summary
from sqlalchemy.ext.asyncio import AsyncSession


_LLM_CACHE: dict[tuple[str, str], ChatGoogleGenerativeAI] = {}
_LLM_CACHE_LOCK = threading.Lock()


def _get_cached_compare_llm(model: str, api_key: str) -> ChatGoogleGenerativeAI:
    cache_key = (model, api_key)
    with _LLM_CACHE_LOCK:
        cached = _LLM_CACHE.get(cache_key)
    if cached is not None:
        return cached

    llm = ChatGoogleGenerativeAI(
        model=model,
        temperature=0,
        google_api_key=api_key,
    )
    with _LLM_CACHE_LOCK:
        _LLM_CACHE.setdefault(cache_key, llm)
        return _LLM_CACHE[cache_key]


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
) -> ConfigResult:
    start = time.perf_counter()

    query_mode = classify_query(query)

    vectorstore = get_or_load_collection(
        config.collection_name,
        config.embedding_provider,
        config.embedding_model,
        user_scope=user_scope,
    )

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY/GOOGLE_API_KEY is not set.")

    llm = _get_cached_compare_llm(model="gemini-2.5-flash", api_key=api_key)

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

        return ConfigResult(
            config=config,
            answer=answer,
            chunks=chunks,
            scores=scores,
            latency_ms=round(latency_ms, 3),
            avg_similarity=calc_avg_similarity(scores),
            chunk_count=len(chunks),
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

    context = "\n\n".join(chunks) if chunks else "No relevant context retrieved."
    prompt = (
        "Context:\n"
        f"{context}\n\n"
        f"Question: {query}\n\n"
        "Answer based only on the context provided."
    )

    try:
        llm_response = await asyncio.to_thread(llm.invoke, prompt)
        answer = str(getattr(llm_response, "content", "")).strip()
    except Exception as exc:
        answer = f"[LLM Error: {str(exc)}]"

    end = time.perf_counter()
    latency_ms = (end - start) * 1000.0

    return ConfigResult(
        config=config,
        answer=answer,
        chunks=chunks,
        scores=scores,
        latency_ms=round(latency_ms, 3),
        avg_similarity=calc_avg_similarity(scores),
        chunk_count=len(chunks),
    )


async def run_comparison(
    query: str,
    configs: List[RAGConfig],
    user_scope: str | None = None,
    db: AsyncSession | None = None,
) -> List[ConfigResult]:
    results: List[ConfigResult] = []
    for cfg in configs:
        result = await run_single_config(query=query, config=cfg, user_scope=user_scope, db=db)
        results.append(result)
    return results
