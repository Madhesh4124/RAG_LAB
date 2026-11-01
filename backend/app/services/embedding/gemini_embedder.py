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
        self.model = model or "models/gemini-embedding-001"
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY or GEMINI_API_KEY is not set. "
                "Please add it to your .env file or environment."
            )

        self._embeddings = GoogleGenerativeAIEmbeddings(
            model=self.model,
            google_api_key=api_key,
        )

    @property
    def model_name(self) -> str:
        """The name of the embedding model."""
        return self.model

    def _extract_retry_delay(self, error_msg: str, default_wait: float) -> float:
        import re
        # Google sends: "Please retry in 45.417289074s."
        m = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", error_msg, re.IGNORECASE)
        if m:
            return float(m.group(1)) + 1.5
        # Or: "'retryDelay': '45s'"
        m = re.search(r"['\"]retryDelay['\"]\s*:\s*['\"]([0-9]+)s?['\"]", error_msg, re.IGNORECASE)
        if m:
            return float(m.group(1)) + 1.5
        return default_wait

    def _embed_batch_with_retry(self, texts: List[str]) -> List[List[float]]:
        import time
        max_retries = 6
        for attempt in range(max_retries):
            try:
                return self._embeddings.embed_documents(texts)
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries - 1 and any(token in error_msg for token in ["429", "RESOURCE_EXHAUSTED", "ResourceExhausted", "Quota", "rate limit", "RateLimit"]):
                    exponential_default = min(2 ** (attempt + 1) + 2, 60)
                    wait_time = self._extract_retry_delay(error_msg, exponential_default)
                    logger.warning(
                        "[GeminiEmbedder] Rate limit hit (attempt %s/%s). Waiting exact %ss: %s",
                        attempt + 1, max_retries, round(wait_time, 2), error_msg[:180]
                    )
                    time.sleep(wait_time)
                    continue
                raise

    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string."""
        import time
        max_retries = 6
        for attempt in range(max_retries):
            try:
                return self._embeddings.embed_query(text)
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries - 1 and any(token in error_msg for token in ["429", "RESOURCE_EXHAUSTED", "ResourceExhausted", "Quota", "rate limit", "RateLimit"]):
                    exponential_default = min(2 ** (attempt + 1) + 2, 60)
                    wait_time = self._extract_retry_delay(error_msg, exponential_default)
                    logger.warning(
                        "[GeminiEmbedder] Rate limit hit on embed_query (attempt %s/%s). Waiting exact %ss: %s",
                        attempt + 1, max_retries, round(wait_time, 2), error_msg[:180]
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
        }
