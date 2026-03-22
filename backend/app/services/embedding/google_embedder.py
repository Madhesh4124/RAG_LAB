"""
Google Generative AI embedding strategy.

Uses LangChain's GoogleGenerativeAIEmbeddings to produce vector
embeddings via Google's text-embedding models.
"""

import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from backend.app.services.embedding.base import BaseEmbedder

load_dotenv()


class GoogleEmbedder(BaseEmbedder):
    """Embedder backed by Google Generative AI (via LangChain).

    Args:
        model: The Google embedding model identifier.
               Defaults to ``"models/text-embedding-004"``.

    Raises:
        ValueError: If *GOOGLE_API_KEY* is not set in the environment
                    or ``.env`` file.
    """

    def __init__(self, model: str = "models/text-embedding-004") -> None:
        self.model = model

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY is not set. "
                "Please add it to your .env file."
            )

        self._embeddings = GoogleGenerativeAIEmbeddings(
            model=self.model,
            google_api_key=api_key,
        )

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
        return self._embeddings.embed_query(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings using Google's embedding model.

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
            "strategy": "google_genai",
            "model": self.model,
            "provider": "Google",
        }
