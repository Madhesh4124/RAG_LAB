"""
Base classes for text embedding.

Defines the BaseEmbedder abstract base class that all embedding
strategies must implement.
"""

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Maximum items per embed_batch() call — override via MAX_EMBED_BATCH_SIZE env-var.
# NVIDIA AI Endpoints caps at 96-100 items per request; 96 is a safe default.
_MAX_EMBED_BATCH_SIZE: int = int(os.getenv("MAX_EMBED_BATCH_SIZE", "96"))


class BaseEmbedder(ABC):
    """Abstract base class for all embedding strategies.

    Subclasses must implement `embed_text()` to embed a single string,
    `embed_batch()` to embed a list of strings, and `get_config()` to
    expose the embedder's current configuration, along with a `model_name`
    property.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the embedding model being used."""
        ...

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate an embedding vector for a single text string.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        ...

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a batch of text strings.

        Args:
            texts: A list of texts to embed.

        Returns:
            A list of embedding vectors, one per input text.
        """
        ...

    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Return the embedder's current settings as a dictionary.

        Returns:
            A dict describing the embedder's configuration
            (e.g., model name, provider, strategy).
        """
        ...

    def embed_in_batches(
        self,
        texts: List[str],
        batch_size: int = _MAX_EMBED_BATCH_SIZE,
        sleep_between: float = 0.25,
    ) -> List[List[float]]:
        """Embed *texts* in safe sub-batches to respect provider rate limits (P2.2).

        Splits *texts* into chunks of at most *batch_size* items, calls
        ``embed_batch`` sequentially for each chunk, and concatenates results.
        A short sleep between batches avoids hammering the endpoint.

        Args:
            texts: All texts to embed.
            batch_size: Maximum items per ``embed_batch`` call.
                Defaults to ``MAX_EMBED_BATCH_SIZE`` env-var (96).
            sleep_between: Seconds to wait between sub-batch calls (default 0.25 s).

        Returns:
            A flat list of embedding vectors in the same order as *texts*.
        """
        if not texts:
            return []

        batch_size = max(1, batch_size)
        results: List[List[float]] = []

        for start in range(0, len(texts), batch_size):
            sub_batch = texts[start : start + batch_size]
            logger.debug(
                "%s.embed_in_batches: embedding sub-batch %d-%d / %d",
                type(self).__name__,
                start + 1,
                start + len(sub_batch),
                len(texts),
            )
            results.extend(self.embed_batch(sub_batch))
            if start + batch_size < len(texts) and sleep_between > 0:
                time.sleep(sleep_between)

        return results
