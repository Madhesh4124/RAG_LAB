"""Google Gemini embedding strategy.

Uses LangChain's GoogleGenerativeAIEmbeddings to produce vector
embeddings via Google's Gemini embedding models.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.services.embedding.base import BaseEmbedder

logger = logging.getLogger(__name__)

# Search for .env in current, backend, or project root directory
for env_path in [
    Path(".env"),
    Path("backend/.env"),
    Path(__file__).resolve().parents[3] / ".env",
    Path(__file__).resolve().parents[2] / ".env",
]:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        break


class GeminiEmbedder(BaseEmbedder):
    """Embedder backed by Google Gemini API (via LangChain).

    Supported models include:
      - models/gemini-embedding-001 (3072-dim)
      - models/gemini-embedding-2-preview (3072-dim)
    """

    def __init__(self, model: str = "models/gemini-embedding-001") -> None:
        import threading
        self.model = model or "models/gemini-embedding-001"
        self._keys = self._collect_api_keys()
        if not self._keys:
            raise ValueError(
                "Neither GOOGLE_API_KEY nor GEMINI_API_KEY is set. "
                "Please configure at least one in your environment."
            )

        self._clients = [
            GoogleGenerativeAIEmbeddings(model=self.model, google_api_key=k)
            for k in self._keys
        ]
        self._current_index = 0
        self._lock = threading.Lock()
        logger.info(
            "[GeminiEmbedder] Initialized with %d API key(s) in round-robin pool for model %s",
            len(self._clients),
            self.model,
        )

    def _collect_api_keys(self) -> List[str]:
        keys: List[str] = []
        for var_name in ["GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEYS"]:
            raw = os.getenv(var_name, "").strip()
            if not raw:
                continue
            for part in raw.split(","):
                key = part.strip()
                if key and key not in keys:
                    keys.append(key)
        return keys

    def _get_next_client(self) -> GoogleGenerativeAIEmbeddings:
        with self._lock:
            client = self._clients[self._current_index % len(self._clients)]
            self._current_index += 1
            return client

    @property
    def model_name(self) -> str:
        """The name of the embedding model."""
        return self.model

    def _extract_retry_delay(self, error_msg: str, default_wait: float) -> float:
        import re
        m = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", error_msg, re.IGNORECASE)
        if m:
            return float(m.group(1)) + 1.5
        m = re.search(r"['\"]retryDelay['\"]\s*:\s*['\"]([0-9]+)s?['\"]", error_msg, re.IGNORECASE)
        if m:
            return float(m.group(1)) + 1.5
        return default_wait

    def _embed_batch_with_retry(self, texts: List[str]) -> List[List[float]]:
        import time
        max_retries = max(6, len(self._clients) * 3)
        for attempt in range(max_retries):
            client = self._get_next_client()
            try:
                return client.embed_documents(texts)
            except Exception as e:
                error_msg = str(e)
                is_rate_limit = any(
                    token in error_msg
                    for token in ["429", "RESOURCE_EXHAUSTED", "ResourceExhausted", "Quota", "rate limit", "RateLimit"]
                )
                if attempt < max_retries - 1:
                    if is_rate_limit and len(self._clients) > 1 and attempt < len(self._clients):
                        logger.warning(
                            "[GeminiEmbedder] Key rate limited on attempt %s. Rotating to alternative key.",
                            attempt + 1,
                        )
                        continue

                    if is_rate_limit:
                        exponential_default = min(2 ** (attempt + 1) + 2, 60)
                        wait_time = self._extract_retry_delay(error_msg, exponential_default)
                        logger.warning(
                            "[GeminiEmbedder] Rate limit hit across keys (attempt %s/%s). Waiting %ss.",
                            attempt + 1,
                            max_retries,
                            round(wait_time, 2),
                        )
                        time.sleep(wait_time)
                        continue
                raise

    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string."""
        import time
        max_retries = max(6, len(self._clients) * 3)
        for attempt in range(max_retries):
            client = self._get_next_client()
            try:
                return client.embed_query(text)
            except Exception as e:
                error_msg = str(e)
                is_rate_limit = any(
                    token in error_msg
                    for token in ["429", "RESOURCE_EXHAUSTED", "ResourceExhausted", "Quota", "rate limit", "RateLimit"]
                )
                if attempt < max_retries - 1:
                    if is_rate_limit and len(self._clients) > 1 and attempt < len(self._clients):
                        logger.warning(
                            "[GeminiEmbedder] Key rate limited on embed_query. Rotating to alternative key.",
                        )
                        continue

                    if is_rate_limit:
                        exponential_default = min(2 ** (attempt + 1) + 2, 60)
                        wait_time = self._extract_retry_delay(error_msg, exponential_default)
                        logger.warning(
                            "[GeminiEmbedder] Rate limit hit on embed_query (attempt %s/%s). Waiting %ss.",
                            attempt + 1,
                            max_retries,
                            round(wait_time, 2),
                        )
                        time.sleep(wait_time)
                        continue
                raise

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings with automatic rate limit backoff."""
        return self._embed_batch_with_retry(texts)

    def get_config(self) -> Dict[str, Any]:
        """Return the embedder's configuration."""
        return {
            "strategy": "gemini",
            "model": self.model,
            "provider": "Google Gemini",
            "keys_loaded": len(self._clients),
        }
