"""
RAG Pipeline.

Orchestrates the chunking, embedding, and vector storage components
into a single, unified workflow.
"""

from typing import Any, Dict, List, Tuple

from backend.app.services.chunking.base import BaseChunker, Chunk
from backend.app.services.embedding.base import BaseEmbedder
from backend.app.services.vectorstore.base import BaseVectorStore


class RAGPipeline:
    """Unified RAG pipeline coordinating chunking, embedding, and storage.

    Args:
        chunker: The strategy to use for document chunking.
        embedder: The strategy to use for vectorizing chunks and queries.
        vectorstore: The storage strategy for indexing and retrieving chunks.
    """

    def __init__(
        self,
        chunker: BaseChunker,
        embedder: BaseEmbedder,
        vectorstore: BaseVectorStore,
    ) -> None:
        self.chunker = chunker
        self.embedder = embedder
        self.vectorstore = vectorstore

    def index_document(self, text: str, doc_id: str, metadata: dict) -> None:
        """Processes a document and indexes it into the vector store.

        Args:
            text: The full textual content of the document.
            doc_id: A unique identifier for the document.
            metadata: Additional metadata to associate with the chunks.
        """
        # Ensure doc_id is available in the metadata so it stays connected to the chunks
        enriched_metadata = metadata.copy() if metadata else {}
        enriched_metadata["doc_id"] = doc_id

        # 1. Chunk the document
        chunks = self.chunker.chunk(text=text, metadata=enriched_metadata)

        # 2. Embed and store the chunks
        self.vectorstore.add_chunks(chunks=chunks, embedder=self.embedder)

    def retrieve(self, query: str, top_k: int = 5) -> List[Tuple[Chunk, float]]:
        """Retrieves chunks similar to the query.

        Args:
            query: The search query string.
            top_k: The maximum number of results to fetch.

        Returns:
            A list of tuples, each containing a Chunk and a syntactic similarity score.
        """
        return self.vectorstore.search(
            query=query, embedder=self.embedder, top_k=top_k
        )

    def get_config(self) -> Dict[str, Any]:
        """Returns the fully assembled pipeline configuration.

        Returns:
            A dictionary containing the individual configurations of the
            chunker, embedder, and vectorstore.
        """
        return {
            "chunker": self.chunker.get_config(),
            "embedder": self.embedder.get_config(),
            "vectorstore": self.vectorstore.get_config(),
        }
