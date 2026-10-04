import json
import logging
import math
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from app.services.chunking.base import Chunk


def _get_evaluator_llm(llm_client: Any = None) -> Any:
    """Get the LLM model to use for evaluation.

    Prefers the dedicated EVALUATION_LLM (Groq / openai/gpt-oss-120b) as configured in .env,
    falling back to llm_client.fallback_client or llm_client.llm if needed.
    """
    if llm_client is not None:
        target = getattr(llm_client, "llm", llm_client)
        if "mock" in type(target).__name__.lower() or "mock" in type(llm_client).__name__.lower():
            return target

    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            groq_api_key = os.getenv("GROQ_API_KEY")
        except Exception:
            pass
    eval_provider = os.getenv("EVALUATION_LLM_PROVIDER", "groq")
    eval_model = os.getenv("EVALUATION_LLM_MODEL", "openai/gpt-oss-120b")

    # 1. Prefer Groq if available for ultra-fast (sub-second) evaluation
    if groq_api_key:
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=eval_model,
                temperature=0.0,
                api_key=groq_api_key,
                max_tokens=2048,
                max_retries=1,
                request_timeout=15.0,
                model_kwargs={"response_format": {"type": "json_object"}},
            )
        except Exception as e:
            logger.warning("Could not initialize dedicated Groq evaluation LLM: %s", e)

    # 2. NVIDIA NIM fallback with 15s timeout and thinking disabled
    nvidia_api_key = os.getenv("NVIDIA_API_KEY")
    if nvidia_api_key:
        try:
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            return ChatNVIDIA(
                model="nvidia/nemotron-3.5-lightning-30b-a3b",
                api_key=nvidia_api_key,
                temperature=0.0,
                max_completion_tokens=1024,
                timeout=15.0,
                model_kwargs={"chat_template_kwargs": {"enable_thinking": False}},
            )
        except Exception as e:
            logger.warning("Could not initialize fallback NVIDIA evaluation LLM: %s", e)

    if llm_client is not None:
        if hasattr(llm_client, "fallback_client") and llm_client.fallback_client:
            fb = llm_client.fallback_client
            if hasattr(fb, "llm") and fb.llm is not None:
                return fb.llm
        if hasattr(llm_client, "llm") and llm_client.llm is not None:
            return llm_client.llm
        return llm_client
    return None


def _extract_text_content(content: Any) -> str:
    """Safely convert LLM response content to a plain string.

    Gemini (and other LLMs) can return content as:
    - a plain str
    - a list of content blocks (e.g. [{"type": "thinking", ...}, {"type": "text", "text": "..."}])
    - a dict
    This helper extracts only the text parts, discarding thinking/reasoning blocks.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (int, float, bool)):
        return str(content)
    if isinstance(content, dict):
        if content.get("type") in {"thinking", "thought"}:
            return ""
        for key in ("text", "output_text", "content", "parts"):
            val = content.get(key)
            if val is not None:
                extracted = _extract_text_content(val)
                if extracted:
                    return extracted
        return ""
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            text = _extract_text_content(item)
            if text:
                parts.append(text)
        return "".join(parts)
    return str(content)


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
            metadata = getattr(chunk, "metadata")
            return float(metadata.get("score", metadata.get("raw_score", 0.0)))
        except (TypeError, ValueError):
            return 0.0
    if isinstance(chunk, dict):
        try:
            return float(chunk.get("score", chunk.get("raw_score", 0.0)))
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
    metadata = dict(_chunk_metadata(chunk))
    score = _chunk_score(chunk)
    if score:
        metadata.setdefault("score", score)
    return Chunk(text=_chunk_text(chunk), metadata=metadata)


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

    values = []
    for item in payload[:expected_len]:
        if isinstance(item, bool):
            values.append(item)
        elif isinstance(item, str):
            values.append(item.strip().lower() in {"true", "yes", "1"})
        else:
            values.append(bool(item))
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


def judge_chunk_relevance(query: str, chunks: List[Any], llm_client: Any = None, allow_llm_judge: bool = False) -> List[bool]:
    if not chunks or not allow_llm_judge or llm_client is None:
        return _heuristic_relevance(query, chunks)

    llm = _get_evaluator_llm(llm_client)
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
    except Exception as exc:
        logger.warning("Primary evaluator failed in judge_chunk_relevance: %s", exc)
        if hasattr(llm_client, "fallback_client") and llm_client.fallback_client:
            fb = llm_client.fallback_client
            if hasattr(fb, "llm") and fb.llm is not None and fb.llm != llm:
                try:
                    response = fb.llm.invoke(prompt)
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
    precomputed_retrieved_flags: Optional[List[bool]] = None,
    precomputed_candidate_flags: Optional[List[bool]] = None,
    allow_llm_judge: bool = False,
) -> Dict[str, Any]:
    retrieval_config = retrieval_config or {}
    normalized_retrieved = [_normalize_chunk(chunk) for chunk in retrieved_chunks]
    normalized_candidates = [_normalize_chunk(chunk) for chunk in (candidate_chunks or retrieved_chunks)]

    if precomputed_retrieved_flags is not None:
        retrieved_flags = precomputed_retrieved_flags
    elif allow_llm_judge and llm_client is not None:
        retrieved_flags = judge_chunk_relevance(query, normalized_retrieved, llm_client=llm_client, allow_llm_judge=True)
    else:
        retrieved_flags = _heuristic_relevance(query, normalized_retrieved)

    if precomputed_candidate_flags is not None:
        candidate_flags = precomputed_candidate_flags
    elif allow_llm_judge and llm_client is not None:
        candidate_flags = judge_chunk_relevance(query, normalized_candidates, llm_client=llm_client, allow_llm_judge=True)
    else:
        candidate_flags = _heuristic_relevance(query, normalized_candidates)

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

    # Compute robust heuristic fallback estimates if LLM evaluation is absent
    heuristic_faithfulness = 0.5 if (answer and not answer.startswith("[LLM Error")) else None
    heuristic_relevancy = 0.5 if (answer and not answer.startswith("[LLM Error")) else None
    if answer and not answer.startswith("[LLM Error"):
        ans_terms = _tokenize(answer)
        if ans_terms:
            ctx_text = " ".join(_chunk_text(c) for c in retrieved_chunks)
            ctx_terms = _tokenize(ctx_text)
            overlap_ctx = len(ans_terms & ctx_terms)
            heuristic_faithfulness = round(min(1.0, max(0.0, overlap_ctx / max(1, len(ans_terms)))), 3)

        q_terms = _tokenize(query)
        if q_terms and ans_terms:
            overlap_q = len(q_terms & ans_terms)
            heuristic_relevancy = round(min(1.0, max(0.0, overlap_q / max(1, len(q_terms)))), 3)

    answer_metrics = {
        "faithfulness": heuristic_faithfulness,
        "answer_relevancy": heuristic_relevancy,
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


def _parse_evaluator_json(content: str) -> Dict[str, Any]:
    """Parse JSON from evaluator response, gracefully stripping thinking preambles and code fences."""
    if not content:
        return {}
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", content, flags=re.IGNORECASE).strip()

    # 1. Code fence matching
    fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", cleaned, flags=re.IGNORECASE)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except Exception:
            pass

    # 2. Direct JSON decode
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # 3. Scan for JSON objects using raw_decode to skip thoughts/preambles
    decoder = json.JSONDecoder()
    best_candidate: Dict[str, Any] = {}
    pos = 0
    target_keys = ("faithfulness", "answer_relevancy", "context_recall", "retrieved_relevance", "candidate_relevance")
    while True:
        pos = cleaned.find("{", pos)
        if pos == -1:
            break
        try:
            obj, _ = decoder.raw_decode(cleaned[pos:])
            if isinstance(obj, dict):
                matching_keys = sum(1 for k in target_keys if k in obj)
                if matching_keys > len(best_candidate):
                    best_candidate = obj
                    if matching_keys >= 3:
                        return best_candidate
        except Exception:
            pass
        pos += 1

    if best_candidate:
        return best_candidate

    # 4. Regex fallback extraction
    data: Dict[str, Any] = {}
    f_match = re.search(r'["\']faithfulness["\']\s*:\s*([0-9.]+)', cleaned)
    if f_match:
        try:
            data["faithfulness"] = float(f_match.group(1))
        except ValueError:
            pass
    r_match = re.search(r'["\']answer_relevancy["\']\s*:\s*([0-9.]+)', cleaned)
    if r_match:
        try:
            data["answer_relevancy"] = float(r_match.group(1))
        except ValueError:
            pass
    c_match = re.search(r'["\']context_recall["\']\s*:\s*([0-9.]+)', cleaned)
    if c_match:
        try:
            data["context_recall"] = float(c_match.group(1))
        except ValueError:
            pass

    return data


def unified_deep_evaluation(
    query: str,
    answer: str,
    retrieved_chunks: List[Any],
    candidate_chunks: List[Any],
    llm_client: Any = None,
) -> Dict[str, Any]:
    evaluator = _get_evaluator_llm(llm_client)
    if not evaluator:
        raise ValueError("No evaluator LLM is available for unified evaluation.")

    # Format the retrieved chunks with safe length limits to prevent token explosions
    retrieved_texts = [
        f"[{idx + 1}] {_chunk_text(c)[:800]}" for idx, c in enumerate(retrieved_chunks)
    ]
    retrieved_formatted = "\n\n".join(retrieved_texts)

    # Format candidate chunks with compact previews
    candidate_texts = [
        f"[{idx + 1}] {_chunk_text(c)[:400]}" for idx, c in enumerate(candidate_chunks)
    ]
    candidate_formatted = "\n\n".join(candidate_texts)

    prompt = (
        "You are an expert RAG system evaluator. Analyze the user query, retrieved chunks, candidate chunks, and generated answer below.\n"
        "CRITICAL: Output ONLY a single raw JSON object matching the exact schema below. Do NOT output thought processes, reasoning, or markdown fences.\n\n"
        "=== INPUTS ===\n"
        f"User Query: {query}\n\n"
        f"Generated Answer: {answer}\n\n"
        f"Retrieved Chunks (Total: {len(retrieved_chunks)}):\n{retrieved_formatted}\n\n"
        f"Candidate Chunks (Total: {len(candidate_chunks)}):\n{candidate_formatted}\n\n"
        "=== TASK ===\n"
        "Evaluate the RAG system performance across the following dimensions. Return JSON ONLY.\n\n"
        "JSON SCHEMA:\n"
        "{\n"
        f"  \"retrieved_relevance\": [list of {len(retrieved_chunks)} booleans, one per retrieved chunk indicating if relevant to query],\n"
        f"  \"candidate_relevance\": [list of {len(candidate_chunks)} booleans, one per candidate chunk indicating if relevant to query],\n"
        "  \"faithfulness\": <float 0.0 to 1.0: Rate how faithful the answer is to ONLY the retrieved chunks. 1.0 means fully grounded.>,\n"
        "  \"answer_relevancy\": <float 0.0 to 1.0: Rate how well the answer addresses the query. 1.0 means perfectly addresses it.>,\n"
        "  \"context_recall\": <float 0.0 to 1.0: Rate if the retrieved chunks fully cover context needed to answer query. 1.0 means fully covers.>\n"
        "}\n"
    )

    content = ""
    try:
        response = evaluator.invoke(prompt)
        raw_content = getattr(response, "content", "")
        content = _extract_text_content(raw_content).strip()
    except Exception as exc:
        logger.warning("Primary evaluator failed in unified_deep_evaluation (%s); attempting fallback", exc)
        if hasattr(llm_client, "fallback_client") and llm_client.fallback_client:
            fb = llm_client.fallback_client
            if hasattr(fb, "llm") and fb.llm is not None and fb.llm != evaluator:
                try:
                    response = fb.llm.invoke(prompt)
                    raw_content = getattr(response, "content", "")
                    content = _extract_text_content(raw_content).strip()
                except Exception as fe:
                    logger.error("Evaluator fallback failed: %s", fe)

    if not content:
        logger.warning("Evaluator returned no content for unified evaluation; falling back to heuristics")

    logger.debug("unified_deep_evaluation raw content: %r", content[:500])

    # Parse JSON output using resilient parser
    data = _parse_evaluator_json(content) if content else {}

    # Extract & validate lists of booleans
    retrieved_flags = data.get("retrieved_relevance")
    if not isinstance(retrieved_flags, list) or len(retrieved_flags) != len(retrieved_chunks):
        retrieved_flags = _heuristic_relevance(query, retrieved_chunks)

    candidate_flags = data.get("candidate_relevance")
    if not isinstance(candidate_flags, list) or len(candidate_flags) != len(candidate_chunks):
        candidate_flags = _heuristic_relevance(query, candidate_chunks)

    # Cast to booleans
    retrieved_flags = [bool(f) for f in retrieved_flags]
    candidate_flags = [bool(f) for f in candidate_flags]

    # Helper to parse floats safely; returns None when the key is absent or unparseable
    def get_float(key: str) -> Optional[float]:
        val = data.get(key)
        if val is None:
            return None
        try:
            return max(0.0, min(1.0, float(val)))
        except (TypeError, ValueError):
            return None

    # Compute baseline heuristic metrics to ensure evaluations NEVER return None
    heuristic_faithfulness = 0.5
    heuristic_relevancy = 0.5
    if answer and not answer.startswith("[LLM Error"):
        ans_terms = _tokenize(answer)
        if ans_terms:
            ctx_text = " ".join(_chunk_text(c) for c in retrieved_chunks)
            ctx_terms = _tokenize(ctx_text)
            overlap_ctx = len(ans_terms & ctx_terms)
            heuristic_faithfulness = round(min(1.0, max(0.0, overlap_ctx / max(1, len(ans_terms)))), 3)

        q_terms = _tokenize(query)
        if q_terms and ans_terms:
            overlap_q = len(q_terms & ans_terms)
            heuristic_relevancy = round(min(1.0, max(0.0, overlap_q / max(1, len(q_terms)))), 3)

    relevant_retrieved = sum(1 for f in retrieved_flags if f)
    relevant_candidates = sum(1 for f in candidate_flags if f)
    heuristic_recall = (relevant_retrieved / max(1, relevant_candidates)) if relevant_candidates else 1.0
    heuristic_recall = round(min(1.0, max(0.0, float(heuristic_recall))), 3)

    faith_val = get_float("faithfulness")
    if faith_val is None:
        faith_val = heuristic_faithfulness

    rel_val = get_float("answer_relevancy")
    if rel_val is None:
        rel_val = heuristic_relevancy

    recall_val = get_float("context_recall")
    if recall_val is None:
        recall_val = heuristic_recall

    return {
        "retrieved_flags": retrieved_flags,
        "candidate_flags": candidate_flags,
        "faithfulness": faith_val,
        "answer_relevancy": rel_val,
        "context_recall": recall_val,
    }
