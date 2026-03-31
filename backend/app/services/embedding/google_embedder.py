"""
Google Generative AI embedding strategy.

Uses LangChain's GoogleGenerativeAIEmbeddings to produce vector
embeddings via Google's text-embedding models.
"""

import os
import random
import re
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.services.embedding.base import BaseEmbedder

load_dotenv(override=True)


class GoogleEmbedder(BaseEmbedder):
    """Embedder backed by Google Generative AI (via LangChain).

    Args:
        model: The Google embedding model identifier.
               Defaults to ``"models/gemini-embedding-2-preview"``.

    Raises:
        ValueError: If *GOOGLE_API_KEY* is not set in the environment
                    or ``.env`` file.
    """

    def __init__(self, model: str = "models/gemini-embedding-2-preview") -> None:
        self.model = model
        self.max_retries = int(os.getenv("GOOGLE_EMBED_MAX_RETRIES", "3"))
        self.base_backoff_seconds = float(os.getenv("GOOGLE_EMBED_BASE_BACKOFF_SECONDS", "2"))
        self.cache_size = int(os.getenv("GOOGLE_EMBED_CACHE_SIZE", "2000"))
        self._cache: "OrderedDict[str, List[float]]" = OrderedDict()

        # 1. Strictly fetch GOOGLE_API_KEY
        api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY is not set in the environment. "
                "Please add 'GOOGLE_API_KEY=your_key' to your .env file."
            )

        # Initialize embeddings with explicit GOOGLE_API_KEY.
        # Do not mutate GEMINI_API_KEY because the same process may
        # also initialize an LLM client in the same request.
        self._embeddings = GoogleGenerativeAIEmbeddings(
            model=self.model,
            google_api_key=api_key,
        )

    def _is_quota_error(self, exc: Exception) -> bool:
        msg = str(exc).upper()
        return "RESOURCE_EXHAUSTED" in msg or "429" in msg

    def _extract_retry_delay(self, message: str) -> Optional[float]:
        patterns = [
            r"retry in\s+([0-9]+(?:\.[0-9]+)?)s",
            r"retryDelay'?:\s*'([0-9]+)s'",
        ]
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return float(match.group(1))
        return None

    def _run_with_retry(self, fn):
        for attempt in range(self.max_retries + 1):
            try:
                return fn()
            except Exception as exc:
                if (not self._is_quota_error(exc)) or attempt >= self.max_retries:
                    raise

                retry_after = self._extract_retry_delay(str(exc)) or 0.0
                exp_backoff = self.base_backoff_seconds * (2 ** attempt)
                delay = max(retry_after, exp_backoff) + random.uniform(0, 0.5)
                time.sleep(delay)

        raise RuntimeError("Embedding retry loop exhausted unexpectedly")

    def _cache_get(self, text: str) -> Optional[List[float]]:
        if text not in self._cache:
            return None
        self._cache.move_to_end(text)
        return self._cache[text]

    def _cache_put(self, text: str, vector: List[float]) -> None:
        if text in self._cache:
            self._cache.move_to_end(text)
        self._cache[text] = vector
        while len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)
    # ── BaseEmbedder interface ──────────────────────────────────────

    @property
    def model_name(self) -> str:
        """The name of the embedding model."""
        return self.model

    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string using Google's embedding model.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        cached = self._cache_get(text)
        if cached is not None:
            return cached

        vector = self._run_with_retry(lambda: self._embeddings.embed_query(text))
        self._cache_put(text, vector)
        return vector

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings using Google's embedding model.

        Args:
            texts: A list of texts to embed.

        Returns:
            A list of embedding vectors, one per input text.
        """
        if not texts:
            return []

        results: List[Optional[List[float]]] = [None] * len(texts)
        missing_positions: List[int] = []
        missing_texts: List[str] = []

        for idx, text in enumerate(texts):
            cached = self._cache_get(text)
            if cached is not None:
                results[idx] = cached
            else:
                missing_positions.append(idx)
                missing_texts.append(text)

        if missing_texts:
            new_vectors = self._run_with_retry(
                lambda: self._embeddings.embed_documents(missing_texts)
            )
            for idx, text, vector in zip(missing_positions, missing_texts, new_vectors):
                self._cache_put(text, vector)
                results[idx] = vector

        if any(vec is None for vec in results):
            raise RuntimeError("Embedding provider returned incomplete batch response")

        return [vec for vec in results if vec is not None]

    def get_config(self) -> Dict[str, Any]:
        """Return the embedder's configuration.

        Returns:
            A dict with *strategy*, *model*, and *provider* keys.
        """
        return {
            "strategy": "google_genai",
            "model": self.model,
            "provider": "Google",
        }
