"""Hugging Face Inference API and Local Embedder strategy.

Uses LangChain's HuggingFaceEndpointEmbeddings with a cooldown/half-open
circuit breaker that falls back to local sentence-transformers on remote
failures and automatically re-probes after transient errors cool down.
"""

import logging
import os
import threading
import time
from typing import Any, Dict, List

from dotenv import load_dotenv

from app.services.embedding.base import BaseEmbedder

load_dotenv()
logger = logging.getLogger(__name__)


def _default_cooldown_seconds() -> float:
    try:
        return max(1.0, float(os.getenv("HF_EMBEDDER_COOLDOWN_SECONDS", "300")))
    except (ValueError, TypeError):
        return 300.0


def _is_permanent_remote_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code is None and getattr(exc, "response", None) is not None:
        status_code = getattr(exc.response, "status_code", None)
    if status_code in (401, 402, 403):
        return True

    msg = str(exc).lower()
    permanent_markers = (
        "402",
        "payment required",
        "401",
        "unauthorized",
        "403",
        "forbidden",
        "invalid token",
        "credits",
    )
    return any(marker in msg for marker in permanent_markers)


class HuggingFaceAPIEmbedder(BaseEmbedder):
    """Embedder backed by Hugging Face Inference API with local fallback."""

    def __init__(
        self,
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
        cooldown_seconds: float | None = None,
    ) -> None:
        self.model = model
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")
        self._remote_embeddings = None
        self._local_embeddings = None

        self._circuit_lock = threading.Lock()
        self._cooldown_seconds = float(
            cooldown_seconds if cooldown_seconds is not None else _default_cooldown_seconds()
        )
        self._circuit_state = "closed"
        self._cooldown_until = 0.0
        self._consecutive_failures = 0

        if self.api_key:
            try:
                from langchain_huggingface import HuggingFaceEndpointEmbeddings
                self._remote_embeddings = HuggingFaceEndpointEmbeddings(
                    model=self.model,
                    huggingfacehub_api_token=self.api_key,
                )
            except Exception as e:
                logger.warning("Could not initialize remote HF endpoint, will use local: %s", e)
                self._circuit_state = "permanently_open"
        else:
            self._circuit_state = "permanently_open"

    def _get_local_embeddings(self):
        if self._local_embeddings is None:
            from langchain_huggingface import HuggingFaceEmbeddings
            logger.info("Initializing local HuggingFaceEmbeddings model=%s", self.model)
            self._local_embeddings = HuggingFaceEmbeddings(model_name=self.model)
        return self._local_embeddings

    def _should_try_remote(self) -> bool:
        with self._circuit_lock:
            if self._remote_embeddings is None or self._circuit_state == "permanently_open":
                return False
            if self._circuit_state == "closed":
                return True
            if self._circuit_state == "open":
                if time.monotonic() >= self._cooldown_until:
                    self._circuit_state = "half_open"
                    return True
                return False
            # Already probing in half_open: let concurrent callers use local embeddings cleanly.
            return False

    def _record_remote_success(self) -> None:
        with self._circuit_lock:
            self._circuit_state = "closed"
            self._cooldown_until = 0.0
            self._consecutive_failures = 0

    def _record_remote_failure(self, exc: Exception) -> None:
        with self._circuit_lock:
            self._consecutive_failures += 1
            if _is_permanent_remote_error(exc):
                logger.warning(
                    "HF remote inference hit unrecoverable error for %s (%s); permanently switching to local embeddings",
                    self.model,
                    exc,
                )
                self._circuit_state = "permanently_open"
                self._cooldown_until = 0.0
                self._remote_embeddings = None
            else:
                self._circuit_state = "open"
                self._cooldown_until = time.monotonic() + self._cooldown_seconds
                logger.warning(
                    "HF remote inference failed for %s (%s); opening circuit for %.1fs and falling back to local embeddings",
                    self.model,
                    exc,
                    self._cooldown_seconds,
                )

    # ── BaseEmbedder interface ──────────────────────────────────────

    @property
    def model_name(self) -> str:
        """The name of the embedding model."""
        return self.model

    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string."""
        if self._should_try_remote():
            try:
                result = self._remote_embeddings.embed_query(text)
                self._record_remote_success()
                return result
            except Exception as exc:
                self._record_remote_failure(exc)
        return self._get_local_embeddings().embed_query(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings."""
        if self._should_try_remote():
            try:
                result = self._remote_embeddings.embed_documents(texts)
                self._record_remote_success()
                return result
            except Exception as exc:
                self._record_remote_failure(exc)
        return self._get_local_embeddings().embed_documents(texts)

    def get_config(self) -> Dict[str, Any]:
        """Return the embedder's configuration."""
        return {
            "strategy": "huggingface_api",
            "model": self.model,
            "provider": "Hugging Face",
        }
