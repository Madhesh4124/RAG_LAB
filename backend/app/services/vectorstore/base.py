"""
Base classes for vector storage.

Defines the BaseVectorStore abstract base class that all
vector store implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from app.services.chunking.base import Chunk
from app.services.embedding.base import BaseEmbedder


class BaseVectorStore(ABC):
    """Abstract base class for all vector store strategies."""

    @abstractmethod
    def add_chunks(self, chunks: List[Chunk], embedder: BaseEmbedder) -> None:
        """Embeds and stores a list of Chunk objects.

        Args:
            chunks: A list of Chunk objects to store.
            embedder: A BaseEmbedder instance to generate embeddings.
        """
        ...

    @abstractmethod
    def search(
        self, query: str, embedder: BaseEmbedder, top_k: int = 5
    ) -> List[Tuple[Chunk, float]]:
        """Searches for chunks similar to the query string.

        Args:
            query: The search string.
            embedder: A BaseEmbedder instance to embed the query.
            top_k: The maximum number of results to return.

        Returns:
            A list of tuples, where each tuple contains a Chunk and a
            similarity score (float).
        """
        ...

    @abstractmethod
    def delete_document(self, doc_id: str) -> None:
        """Removes all chunks associated with a given document ID.

        Args:
            doc_id: The identifier of the document whose chunks should
                    be deleted.
        """
        ...

    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Returns the current settings as a dictionary.

        Returns:
            A dictionary describing the vector store config.
        """
        ...
