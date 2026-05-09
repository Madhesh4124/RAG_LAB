import json
import math
import re
from typing import Any, Dict, List, Optional

from app.services.chunking.base import Chunk


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _chunk_text(chunk: Any) -> str:
    if hasattr(chunk, "text"):
        return _safe_text(getattr(chunk, "text"))
    if isinstance(chunk, dict):
        return _safe_text(chunk.get("text"))
    return _safe_text(chunk)


def _chunk_score(chunk: Any) -> float:
    if hasattr(chunk, "score"):
        try:
            return float(getattr(chunk, "score"))
        except (TypeError, ValueError):
            pass
    if hasattr(chunk, "metadata") and isinstance(getattr(chunk, "metadata"), dict):
        try:
            return float(getattr(chunk, "metadata").get("score", 0.0))
        except (TypeError, ValueError):
            return 0.0
    if isinstance(chunk, dict):
        try:
            return float(chunk.get("score", 0.0))
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def _chunk_metadata(chunk: Any) -> Dict[str, Any]:
    if hasattr(chunk, "metadata") and isinstance(getattr(chunk, "metadata"), dict):
        return getattr(chunk, "metadata")
    if isinstance(chunk, dict) and isinstance(chunk.get("metadata"), dict):
        return chunk["metadata"]
    return {}


def _normalize_chunk(chunk: Any) -> Chunk:
    return Chunk(text=_chunk_text(chunk), metadata=_chunk_metadata(chunk))


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


def _parse_bool_list(raw_text: str, expected_len: int) -> Optional[List[bool]]:
    text = str(raw_text or "").strip()
    if not text:
        return None

    match = re.search(r"\[[\s\S]*\]", text)
    candidate = match.group(0) if match else text
    normalized = candidate.replace("True", "true").replace("False", "false")

    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, list):
        return None

    values = [bool(item) for item in payload[:expected_len]]
    if len(values) < expected_len:
        values.extend([False] * (expected_len - len(values)))
    return values


def _heuristic_relevance(query: str, chunks: List[Any]) -> List[bool]:
    query_terms = _tokenize(query)
    if not query_terms:
        return [False for _ in chunks]

    flags = []
    for chunk in chunks:
        chunk_terms = _tokenize(_chunk_text(chunk))
        overlap = len(query_terms & chunk_terms)
        ratio = overlap / max(1, len(query_terms))
        flags.append(overlap >= 2 or ratio >= 0.35)
    return flags


def judge_chunk_relevance(query: str, chunks: List[Any], llm_client: Any = None) -> List[bool]:
    if not chunks:
        return []

    llm = getattr(llm_client, "llm", None) if llm_client is not None else None
    if llm is None:
        return _heuristic_relevance(query, chunks)

    numbered_chunks = "\n\n".join(
        f"[{idx + 1}] {_chunk_text(chunk)[:1200]}"
        for idx, chunk in enumerate(chunks)
    )
    prompt = (
        "For the user query below, judge whether each chunk is relevant for answering it.\n"
        "Return JSON only as a list of booleans, one per chunk.\n\n"
        f"Query: {query}\n\n"
        f"Chunks:\n{numbered_chunks}"
    )

    try:
        response = llm.invoke(prompt)
        parsed = _parse_bool_list(getattr(response, "content", ""), expected_len=len(chunks))
        if parsed is not None:
            return parsed
    except Exception:
        pass

    return _heuristic_relevance(query, chunks)


def compute_diversity_score(chunks: List[Any], embedder: Any = None) -> Optional[float]:
    if len(chunks) < 2 or embedder is None or not hasattr(embedder, "embed_batch"):
        return None

    texts = [_chunk_text(chunk)[:2000] for chunk in chunks]
    try:
        vectors = embedder.embed_batch(texts)
    except Exception:
        return None

    if not vectors or len(vectors) < 2:
        return None

    similarities: List[float] = []
    for i in range(len(vectors)):
        vi = vectors[i]
        norm_i = math.sqrt(sum(float(x) * float(x) for x in vi))
        if norm_i == 0:
            continue
        for j in range(i + 1, len(vectors)):
            vj = vectors[j]
            norm_j = math.sqrt(sum(float(x) * float(x) for x in vj))
            if norm_j == 0:
                continue
            dot = sum(float(a) * float(b) for a, b in zip(vi, vj))
            cosine = max(-1.0, min(1.0, dot / (norm_i * norm_j)))
            similarities.append(cosine)

    if not similarities:
        return None

    # Map cosine similarity to a 0..1 diversity score.
    return max(0.0, min(1.0, 1.0 - ((sum(similarities) / len(similarities)) + 1.0) / 2.0))


def build_retrieval_metrics_report(
    query: str,
    answer: str,
    retrieved_chunks: List[Any],
    candidate_chunks: Optional[List[Any]] = None,
    llm_client: Any = None,
    embedder: Any = None,
    retrieval_config: Optional[Dict[str, Any]] = None,
    query_mode: Optional[str] = None,
) -> Dict[str, Any]:
    retrieval_config = retrieval_config or {}
    normalized_retrieved = [_normalize_chunk(chunk) for chunk in retrieved_chunks]
    normalized_candidates = [_normalize_chunk(chunk) for chunk in (candidate_chunks or retrieved_chunks)]

    retrieved_flags = judge_chunk_relevance(query, normalized_retrieved, llm_client=llm_client)
    candidate_flags = judge_chunk_relevance(query, normalized_candidates, llm_client=llm_client)

    k = len(normalized_retrieved)
    relevant_retrieved = sum(1 for flag in retrieved_flags if flag)
    relevant_candidates = sum(1 for flag in candidate_flags if flag)

    precision_at_k = (relevant_retrieved / k) if k else 0.0
    recall_at_k = (relevant_retrieved / relevant_candidates) if relevant_candidates else 0.0
    hit_rate_at_k = 1.0 if relevant_retrieved > 0 else 0.0

    reciprocal_rank = 0.0
    for idx, flag in enumerate(retrieved_flags, start=1):
        if flag:
            reciprocal_rank = 1.0 / idx
            break

    precision_prefix_hits = 0
    average_precision = 0.0
    for idx, flag in enumerate(retrieved_flags, start=1):
        if flag:
            precision_prefix_hits += 1
            average_precision += precision_prefix_hits / idx
    if relevant_candidates:
        average_precision /= relevant_candidates

    dcg = sum((1.0 / math.log2(idx + 1)) for idx, flag in enumerate(retrieved_flags, start=1) if flag)
    ideal_hits = min(relevant_candidates, k)
    idcg = sum((1.0 / math.log2(idx + 1)) for idx in range(1, ideal_hits + 1))
    ndcg_at_k = (dcg / idcg) if idcg else 0.0

    diversity_score = compute_diversity_score(normalized_retrieved, embedder=embedder)
    score_values = [_chunk_score(chunk) for chunk in retrieved_chunks]
    avg_similarity = (sum(score_values) / len(score_values)) if score_values else 0.0

    chunk_judgments = []
    for idx, chunk in enumerate(retrieved_chunks, start=1):
        chunk_judgments.append(
            {
                "rank": idx,
                "relevant": bool(retrieved_flags[idx - 1]) if idx - 1 < len(retrieved_flags) else False,
                "score": _chunk_score(chunk),
                "text_preview": _chunk_text(chunk)[:240],
            }
        )

    answer_metrics = {
        "faithfulness": None,
        "answer_relevancy": None,
        "context_precision": precision_at_k,
        "context_recall": recall_at_k,
    }

    return {
        "query": query,
        "answer": answer,
        "query_mode": query_mode or "unknown",
        "summary_mode": (query_mode == "global"),
        "answer_metrics": answer_metrics,
        "retrieval_metrics": {
            "evaluated_k": k,
            "candidate_pool_size": len(normalized_candidates),
            "precision_at_k": precision_at_k,
            "recall_at_k": recall_at_k,
            "hit_rate_at_k": hit_rate_at_k,
            "reciprocal_rank": reciprocal_rank,
            "average_precision": average_precision,
            "ndcg_at_k": ndcg_at_k,
            "relevant_retrieved": relevant_retrieved,
            "relevant_candidates": relevant_candidates,
            "avg_similarity": avg_similarity,
            "diversity_score": diversity_score,
            "retrieval_strategy": retrieval_config.get("retrieval_type", retrieval_config.get("type", "unknown")),
            "mmr_lambda": retrieval_config.get("lambda_mult"),
        },
        "chunk_judgments": chunk_judgments,
        "notes": {
            "recall_basis": "Recall@k is estimated against a judged candidate pool rather than a labeled benchmark set.",
            "relevance_judging": "Chunk relevance uses the configured LLM when available, otherwise a lexical fallback heuristic.",
        },
    }
