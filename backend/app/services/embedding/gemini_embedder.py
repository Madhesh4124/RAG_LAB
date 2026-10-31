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

    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string."""
        return self._embeddings.embed_query(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings."""
        return self._embeddings.embed_documents(texts)

    def get_config(self) -> Dict[str, Any]:
        """Return the embedder's configuration."""
        return {
            "strategy": "gemini",
            "model": self.model,
            "provider": "Google Gemini",
        }
