import asyncio
import os
import threading
import time
from typing import List, Tuple

from langchain_google_genai import ChatGoogleGenerativeAI

from app.compare.schemas import ConfigResult, RAGConfig
from app.compare.collection_registry import get_or_load_collection
from app.compare.utils import calc_avg_similarity, filter_by_threshold


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


async def run_single_config(
    query: str,
    config: RAGConfig,
    user_scope: str | None = None,
) -> ConfigResult:
    start = time.perf_counter()

    vectorstore = get_or_load_collection(
        config.collection_name,
        config.embedding_provider,
        config.embedding_model,
        user_scope=user_scope,
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

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY/GOOGLE_API_KEY is not set.")

    llm = _get_cached_compare_llm(model="gemini-2.5-flash", api_key=api_key)

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
) -> List[ConfigResult]:
    results: List[ConfigResult] = []
    for cfg in configs:
        result = await run_single_config(query=query, config=cfg, user_scope=user_scope)
        results.append(result)
    return results
