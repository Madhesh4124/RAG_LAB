"""Base class for retrievers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from app.services.chunking.base import Chunk

class BaseRetriever(ABC):
    """Abstract base class for all retrievers."""

    @abstractmethod
    def search(self, query: str, top_k: int) -> List[Tuple[Chunk, float]]:
        """Search for top chunks matching the query.

        Args:
            query: The search query string.
            top_k: Number of chunks to retrieve.

        Returns:
            A list of tuples, each containing a Chunk and its similarity score.
        """
        ...
