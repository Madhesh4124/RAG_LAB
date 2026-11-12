"""Reranker implementations."""

import logging
import math
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

import requests

from app.services.chunking.base import Chunk

logger = logging.getLogger(__name__)

DEFAULT_NVIDIA_RERANK_MODEL = "nvidia/nemotron-3.5-rerank-8b"
_CROSS_ENCODER_CACHE: Dict[str, Any] = {}
_CROSS_ENCODER_LOCK = threading.Lock()


class CrossEncoderReranker:
    """Reranks retrieved chunks using a local cross-encoder model."""

    def __init__(self, model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model
        self._model = None

    def _load_model(self):
        if self._model is None:
            with _CROSS_ENCODER_LOCK:
                cached = _CROSS_ENCODER_CACHE.get(self.model_name)
                if cached is None:
                    from sentence_transformers import CrossEncoder
                    cached = CrossEncoder(self.model_name)
                    _CROSS_ENCODER_CACHE[self.model_name] = cached
                self._model = cached

    def rerank(self, query: str, results: List[Tuple[Chunk, float]], top_k: int) -> List[Tuple[Chunk, float]]:
        """Reranks the results using the cross-encoder."""
        if not results:
            return []

        self._load_model()

        # Create pairs: (query, chunk text)
        pairs = []
        for chunk, _original_score in results:
            metadata = getattr(chunk, "metadata", {}) or {}
            text = metadata.get("window_text") or (
                chunk.text if hasattr(chunk, "text") else getattr(chunk, "page_content", str(chunk))
            )
            pairs.append((query, text))

        # Predict scores
        scores = self._model.predict(pairs)

        # Combine chunks with new scores
        reranked_results = []
        for i, (chunk, _original_score) in enumerate(results):
            reranked_results.append((chunk, float(scores[i])))

        # Sort descending by new score
        reranked_results.sort(key=lambda x: x[1], reverse=True)

        return reranked_results[:top_k]

    def get_config(self) -> dict:
        return {
            "strategy": "cross_encoder",
            "model": self.model_name,
        }


class NvidiaReranker:
    """Reranks chunks using NVIDIA NIM retrieval reranking API."""

    def __init__(
        self,
        model: str = DEFAULT_NVIDIA_RERANK_MODEL,
        timeout_seconds: int = 10,
        max_candidates: int = 8,
        min_candidates: int = 3,
        api_url: Optional[str] = None,
    ):
        self.model_name = model or DEFAULT_NVIDIA_RERANK_MODEL
        self.timeout_seconds = max(1, int(timeout_seconds))
        self.max_candidates = max(1, int(max_candidates))
        self.min_candidates = max(2, int(min_candidates))
        self.api_key = os.getenv("NVIDIA_API_KEY")
        self.endpoint = (
            api_url
            or os.getenv("NVIDIA_RERANK_URL")
            or f"https://ai.api.nvidia.com/v1/retrieval/{self.model_name}/reranking"
        )
        self.session = requests.Session()

    def _headers(self) -> dict:
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY is required for NVIDIA reranking")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _build_passages(candidates: List[Tuple[Chunk, float]]) -> List[Dict[str, str]]:
        passages: List[Dict[str, str]] = []
        for chunk, _ in candidates:
            metadata = getattr(chunk, "metadata", {}) or {}
            text = (
                metadata.get("window_text")
                or (chunk.text if hasattr(chunk, "text") else getattr(chunk, "page_content", str(chunk)))
            )
            passage: Dict[str, str] = {"text": str(text or "")}
            image_uri = metadata.get("image") or metadata.get("image_data_uri")
            if isinstance(image_uri, str) and image_uri.startswith("data:image/"):
                passage["image"] = image_uri
            passages.append(passage)
        return passages

    def _call_api(self, payload: dict) -> dict:
        headers = self._headers()
        last_exc: Optional[Exception] = None
        for attempt in range(2):
            try:
                response = self.session.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout_seconds,
                )
                if response.status_code in (429, 502, 503, 504) and attempt == 0:
                    time.sleep(1.0)
                    continue
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last_exc = exc
                if attempt == 0 and any(code in str(exc) for code in ("429", "502", "503", "504")):
                    time.sleep(1.0)
                    continue
                raise
        raise last_exc or RuntimeError("NVIDIA reranker request failed")

    def rerank(self, query: str, results: List[Tuple[Chunk, float]], top_k: int) -> List[Tuple[Chunk, float]]:
        if not results:
            return []

        if not self.api_key:
            logger.warning("NVIDIA_API_KEY is not set; skipping reranking and returning base results.")
            return results[:top_k]

        candidate_count = min(len(results), max(top_k, self.max_candidates))
        candidates = results[:candidate_count]
        payload = {
            "model": self.model_name,
            "query": {"text": query},
            "passages": self._build_passages(candidates),
        }

        try:
            body = self._call_api(payload)
            rankings = body.get("rankings") if isinstance(body, dict) else None
            if not isinstance(rankings, list) or not rankings:
                return results[:top_k]

            scored_entries: List[Tuple[int, float]] = []
            seen_indices = set()
            for entry in rankings:
                if not isinstance(entry, dict) or "index" not in entry:
                    continue
                idx = int(entry["index"])
                if idx < 0 or idx >= len(candidates) or idx in seen_indices:
                    continue
                raw_score = entry.get("logit")
                if raw_score is None:
                    raw_score = entry.get("score", entry.get("relevance_score"))
                if not isinstance(raw_score, (int, float)) or not math.isfinite(float(raw_score)):
                    continue
                seen_indices.add(idx)
                scored_entries.append((idx, float(raw_score)))

            if not scored_entries:
                return results[:top_k]

            # Convert unbounded logits (e.g. -2.78, -6.28) to monotonic (0, 1] scores
            # while strictly preserving the reranker's ranking order.
            max_logit = max(logit for _, logit in scored_entries)
            reranked_results: List[Tuple[Chunk, float]] = [
                (candidates[idx][0], math.exp(max(-50.0, logit - max_logit)))
                for idx, logit in scored_entries
            ]
            reranked_results.sort(key=lambda item: item[1], reverse=True)

            # Append any candidates omitted by API cleanly after ranked items.
            for idx, (chunk, orig_score) in enumerate(candidates):
                if idx not in seen_indices:
                    reranked_results.append((chunk, float(orig_score)))

            return reranked_results[:top_k]
        except Exception as exc:
            logger.warning("NVIDIA reranking failed (%s); falling back to initial retrieval order.", exc)
            return results[:top_k]

    def get_config(self) -> dict:
        return {
            "strategy": "nvidia",
            "model": self.model_name,
            "timeout_seconds": self.timeout_seconds,
            "max_candidates": self.max_candidates,
            "min_candidates": self.min_candidates,
        }


class HuggingFaceAPIReranker:
    """Reranks chunks using Hugging Face Inference API (no local model download)."""

    def __init__(
        self,
        model: str = "BAAI/bge-reranker-v2-m3",
        timeout_seconds: int = 5,
        max_candidates: int = 6,
        max_workers: int = 4,
        min_candidates: int = 3,
    ):
        self.model_name = model
        self.timeout_seconds = timeout_seconds
        self.max_candidates = max(1, int(max_candidates))
        self.max_workers = max(1, int(max_workers))
        self.min_candidates = max(2, int(min_candidates))
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")
        self.endpoint = f"https://router.huggingface.co/hf-inference/models/{self.model_name}"
        self.session = requests.Session()

    def _headers(self) -> dict:
        if not self.api_key:
            raise ValueError("HUGGINGFACE_API_KEY is required for API-based reranking")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _extract_score(item: Any) -> float:
        if isinstance(item, (int, float)):
            return float(item)

        if isinstance(item, dict):
            for key in ("score", "relevance_score", "logit"):
                value = item.get(key)
                if isinstance(value, (int, float)):
                    return float(value)

        if isinstance(item, list) and item:
            if isinstance(item[0], list):
                return HuggingFaceAPIReranker._extract_score(item[0])

            dict_scores = [
                float(entry.get("score"))
                for entry in item
                if isinstance(entry, dict) and isinstance(entry.get("score"), (int, float))
            ]
            if dict_scores:
                return max(dict_scores)

            numeric = [float(v) for v in item if isinstance(v, (int, float))]
            if numeric:
                return max(numeric)

        return 0.0

    def _call_api(self, payload: dict) -> Any:
        response = self.session.post(
            self.endpoint,
            json=payload,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def _score_batch(self, query: str, texts: List[str]) -> List[float]:
        """Try batch scoring in one API request to reduce round trips."""
        if not texts:
            return []

        payload_options = [
            {"inputs": [{"text": query, "text_pair": text} for text in texts]},
            {"inputs": {"source_sentence": query, "sentences": texts}},
        ]

        for payload in payload_options:
            try:
                response = self._call_api(payload)
                if isinstance(response, list) and len(response) == 1 and isinstance(response[0], list):
                    response = response[0]

                if isinstance(response, list):
                    scores = [self._extract_score(item) for item in response]
                    if len(scores) == len(texts):
                        return scores
                if isinstance(response, dict) and isinstance(response.get("scores"), list):
                    scores = [self._extract_score(item) for item in response["scores"]]
                    if len(scores) == len(texts):
                        return scores
            except Exception:
                continue

        raise ValueError("Reranker batch API did not return parseable scores")

    def _score_pair(self, query: str, text: str) -> float:
        payload_options = [
            {"inputs": [{"text": query, "text_pair": text}]},
            {"inputs": {"text": query, "text_pair": text}},
            {"inputs": [query, text]},
        ]

        for payload in payload_options:
            try:
                response = self._call_api(payload)
                if isinstance(response, list) and response:
                    return self._extract_score(response[0] if isinstance(response[0], (dict, list, int, float)) else response)
                return self._extract_score(response)
            except Exception:
                continue

        raise ValueError("Reranker API did not return a parseable score")

    def rerank(self, query: str, results: List[Tuple[Chunk, float]], top_k: int) -> List[Tuple[Chunk, float]]:
        if not results:
            return []

        if not self.api_key:
            return results[:top_k]

        try:
            candidate_count = min(len(results), max(top_k, self.max_candidates))
            candidates = results[:candidate_count]

            texts = [
                (getattr(chunk, "metadata", {}) or {}).get("window_text")
                or (chunk.text if hasattr(chunk, "text") else getattr(chunk, "page_content", str(chunk)))
                for chunk, _ in candidates
            ]

            try:
                batch_scores = self._score_batch(query, texts)
                reranked_results = [
                    (candidates[i][0], float(batch_scores[i]))
                    for i in range(len(candidates))
                ]
                reranked_results.sort(key=lambda x: x[1], reverse=True)
                return reranked_results[:top_k]
            except Exception:
                pass

            reranked_results = []
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(candidates))) as pool:
                future_to_item = {
                    pool.submit(self._score_pair, query, texts[i]): (i, candidates[i])
                    for i in range(len(candidates))
                }
                for future in as_completed(future_to_item):
                    i, (chunk, original_score) = future_to_item[future]
                    try:
                        score = float(future.result())
                    except Exception:
                        score = float(original_score)
                    reranked_results.append((chunk, score))

            reranked_results.sort(key=lambda x: x[1], reverse=True)
            return reranked_results[:top_k]
        except Exception:
            return results[:top_k]

    def get_config(self) -> dict:
        return {
            "strategy": "huggingface_api",
            "model": self.model_name,
            "timeout_seconds": self.timeout_seconds,
            "max_candidates": self.max_candidates,
            "max_workers": self.max_workers,
            "min_candidates": self.min_candidates,
        }


def get_reranker(config: Dict[str, Any]):
    """Instantiate the configured reranker strategy."""
    provider = str(config.get("provider") or "nvidia").strip().lower()
    model_name = config.get("model") or DEFAULT_NVIDIA_RERANK_MODEL
    timeout_seconds = int(config.get("timeout_seconds", 10))
    max_candidates = int(config.get("max_candidates", 8))
    max_workers = int(config.get("max_workers", 4))
    min_candidates = int(config.get("min_candidates", 3))

    if provider in ("nvidia", "nvidia_api", "nvidia_nim", "nemotron") or str(model_name).startswith("nvidia/"):
        return NvidiaReranker(
            model=model_name,
            timeout_seconds=timeout_seconds,
            max_candidates=max_candidates,
            min_candidates=min_candidates,
        )

    if provider in ("huggingface_api", "huggingface", "hf_api"):
        return HuggingFaceAPIReranker(
            model=model_name,
            timeout_seconds=timeout_seconds,
            max_candidates=max_candidates,
            max_workers=max_workers,
            min_candidates=min_candidates,
        )

    return CrossEncoderReranker(model=model_name)
