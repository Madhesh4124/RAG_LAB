"""Reranker implementations."""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Any

import requests

from app.services.chunking.base import Chunk

class CrossEncoderReranker:
    """Reranks retrieved chunks using a cross-encoder model."""

    def __init__(self, model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.model_name)

    def rerank(self, query: str, results: List[Tuple[Chunk, float]], top_k: int) -> List[Tuple[Chunk, float]]:
        """Reranks the results using the cross-encoder."""
        if not results:
            return []

        self._load_model()

        # Create pairs: (query, chunk text)
        pairs = []
        for chunk, original_score in results:
            metadata = getattr(chunk, "metadata", {}) or {}
            text = metadata.get("window_text") or (chunk.text if hasattr(chunk, "text") else getattr(chunk, "page_content", str(chunk)))
            pairs.append((query, text))

        # Predict scores
        scores = self._model.predict(pairs)

        # Combine chunks with new scores
        reranked_results = []
        for i, (chunk, original_score) in enumerate(results):
            reranked_results.append((chunk, float(scores[i])))

        # Sort descending by new score
        reranked_results.sort(key=lambda x: x[1], reverse=True)

        return reranked_results[:top_k]

    def get_config(self) -> dict:
        return {
            "strategy": "cross_encoder",
            "model": self.model_name
        }


class HuggingFaceAPIReranker:
    """Reranks chunks using Hugging Face Inference API (no local model download)."""

    def __init__(
        self,
        model: str = "BAAI/bge-reranker-v2-m3",
        timeout_seconds: int = 10,
        max_candidates: int = 20,
        max_workers: int = 4,
        min_candidates: int = 8,
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
            # Some endpoints return a list of label-score objects.
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
            {"inputs": {"source_sentence": query, "sentences": texts}},
            {"inputs": [{"text": query, "text_pair": text} for text in texts]},
        ]

        for payload in payload_options:
            try:
                response = self._call_api(payload)
                if isinstance(response, list):
                    # Common response forms:
                    # - [float, float, ...]
                    # - [{"score": ...}, ...]
                    scores = [self._extract_score(item) for item in response]
                    if len(scores) == len(texts):
                        return scores
                # Some endpoints return {"scores": [...]}.
                if isinstance(response, dict) and isinstance(response.get("scores"), list):
                    scores = [self._extract_score(item) for item in response["scores"]]
                    if len(scores) == len(texts):
                        return scores
            except Exception:
                continue

        raise ValueError("Reranker batch API did not return parseable scores")

    def _score_pair(self, query: str, text: str) -> float:
        payload_options = [
            {"inputs": {"text": query, "text_pair": text}},
            {"inputs": [query, text]},
            {"inputs": f"{query} [SEP] {text}"},
        ]

        for payload in payload_options:
            try:
                response = self._call_api(payload)
                if isinstance(response, list) and response:
                    return self._extract_score(response)
                return self._extract_score(response)
            except Exception:
                continue

        raise ValueError("Reranker API did not return a parseable score")

    def rerank(self, query: str, results: List[Tuple[Chunk, float]], top_k: int) -> List[Tuple[Chunk, float]]:
        if not results:
            return []

        if not self.api_key:
            # Fast fallback when API key is missing.
            return results[:top_k]

        try:
            candidate_count = min(len(results), max(top_k, self.max_candidates))
            candidates = results[:candidate_count]

            texts = [
                (getattr(chunk, "metadata", {}) or {}).get("window_text")
                or (chunk.text if hasattr(chunk, "text") else getattr(chunk, "page_content", str(chunk)))
                for chunk, _ in candidates
            ]

            # Fast path: try one batched request.
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

            # Fallback: score pairs concurrently to reduce wall-clock time.
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
            # Do not break retrieval flow if external reranker fails.
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
