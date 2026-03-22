"""
NVIDIA AI Endpoints embedding strategy.

Uses LangChain's NVIDIAEmbeddings to produce vector
embeddings via NVIDIA's text-embedding models.
"""

import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

from app.services.embedding.base import BaseEmbedder

load_dotenv()


class NvidiaEmbedder(BaseEmbedder):
    """Embedder backed by NVIDIA AI Endpoints (via LangChain).

    Args:
        model: The NVIDIA embedding model identifier.
               Defaults to ``"nvidia/nv-embed-v2"``.

    Raises:
        ValueError: If *NVIDIA_API_KEY* is not set in the environment
                    or ``.env`` file.
    """

    def __init__(self, model: str = "nvidia/nv-embed-v2") -> None:
        self.model = model

        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError(
                "NVIDIA_API_KEY is not set. "
                "Please add it to your .env file."
            )

        self._embeddings = NVIDIAEmbeddings(
            model=self.model,
            api_key=api_key,
        )

    # ── BaseEmbedder interface ──────────────────────────────────────

    @property
    def model_name(self) -> str:
        """The name of the embedding model."""
        return self.model

    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string using NVIDIA's embedding model.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        return self._embeddings.embed_query(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings using NVIDIA's embedding model.

        Args:
            texts: A list of texts to embed.

        Returns:
            A list of embedding vectors, one per input text.
        """
        return self._embeddings.embed_documents(texts)

    def get_config(self) -> Dict[str, Any]:
        """Return the embedder's configuration.

        Returns:
            A dict with *strategy*, *model*, and *provider* keys.
        """
        return {
            "strategy": "nvidia_ai_endpoints",
            "model": self.model,
            "provider": "NVIDIA",
        }
