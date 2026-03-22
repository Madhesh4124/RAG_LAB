"""
Base classes for text embedding.

Defines the BaseEmbedder abstract base class that all embedding
strategies must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


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
