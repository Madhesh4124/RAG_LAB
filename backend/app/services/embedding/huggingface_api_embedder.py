"""
Hugging Face Inference API embedding strategy.

Uses LangChain's HuggingFaceEndpointEmbeddings to produce vector
embeddings via Hugging Face's serverless inference API.
"""

import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.services.embedding.base import BaseEmbedder

load_dotenv()


class HuggingFaceAPIEmbedder(BaseEmbedder):
    """Embedder backed by Hugging Face Inference API (via LangChain).

    Supported models include:
            - sentence-transformers/all-MiniLM-L6-v2
      - BAAI/bge-base-en-v1.5
      - thenlper/gte-base
      - intfloat/e5-base-v2

    Args:
        model: The Hugging Face embedding model identifier.
               Defaults to ``"sentence-transformers/all-MiniLM-L6-v2"``.

    Raises:
        ValueError: If *HUGGINGFACE_API_KEY* is not set in the environment
                    or ``.env`` file.
    """

    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model = model

        api_key = os.getenv("HUGGINGFACE_API_KEY")
        if not api_key:
            raise ValueError(
                "HUGGINGFACE_API_KEY is not set. "
                "Please add it to your .env file."
            )

        self._embeddings = HuggingFaceEndpointEmbeddings(
            model=self.model,
            huggingfacehub_api_token=api_key,
        )

    # ── BaseEmbedder interface ──────────────────────────────────────

    @property
    def model_name(self) -> str:
        """The name of the embedding model."""
        return self.model

    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string using Hugging Face's embedding model.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        return self._embeddings.embed_query(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings using Hugging Face's embedding model.

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
            "strategy": "huggingface_api",
            "model": self.model,
            "provider": "Hugging Face",
        }
