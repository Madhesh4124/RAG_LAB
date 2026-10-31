"""Hugging Face Inference API and Local Embedder strategy.

Uses LangChain's HuggingFaceEndpointEmbeddings with seamless fallback
to local sentence-transformers (HuggingFaceEmbeddings) when HF inference
API credits are exhausted or return 402 Payment Required.
"""

import logging
import os
from typing import Any, Dict, List

from dotenv import load_dotenv

from app.services.embedding.base import BaseEmbedder

load_dotenv()
logger = logging.getLogger(__name__)


class HuggingFaceAPIEmbedder(BaseEmbedder):
    """Embedder backed by Hugging Face Inference API with local fallback."""

    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model = model
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")
        self._remote_embeddings = None
        self._local_embeddings = None

        if self.api_key:
            try:
                from langchain_huggingface import HuggingFaceEndpointEmbeddings
                self._remote_embeddings = HuggingFaceEndpointEmbeddings(
                    model=self.model,
                    huggingfacehub_api_token=self.api_key,
                )
            except Exception as e:
                logger.warning("Could not initialize remote HF endpoint, will use local: %s", e)

    def _get_local_embeddings(self):
        if self._local_embeddings is None:
            from langchain_huggingface import HuggingFaceEmbeddings
            logger.info("Initializing local HuggingFaceEmbeddings model=%s", self.model)
            self._local_embeddings = HuggingFaceEmbeddings(model_name=self.model)
        return self._local_embeddings

    # ── BaseEmbedder interface ──────────────────────────────────────

    @property
    def model_name(self) -> str:
        """The name of the embedding model."""
        return self.model

    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string."""
        if self._remote_embeddings is not None:
            try:
                return self._remote_embeddings.embed_query(text)
            except Exception as exc:
                logger.warning(
                    "HF remote inference failed for %s (%s); switching to local sentence-transformers",
                    self.model,
                    exc,
                )
                self._remote_embeddings = None  # Switch to local for remaining calls
        return self._get_local_embeddings().embed_query(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings."""
        if self._remote_embeddings is not None:
            try:
                return self._remote_embeddings.embed_documents(texts)
            except Exception as exc:
                logger.warning(
                    "HF remote inference failed for %s (%s); switching to local sentence-transformers",
                    self.model,
                    exc,
                )
                self._remote_embeddings = None  # Switch to local for remaining calls
        return self._get_local_embeddings().embed_documents(texts)

    def get_config(self) -> Dict[str, Any]:
        """Return the embedder's configuration."""
        return {
            "strategy": "huggingface_api",
            "model": self.model,
            "provider": "Hugging Face",
        }
