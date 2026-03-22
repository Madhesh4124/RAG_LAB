"""Dense Retriever implementation."""

from typing import Any, Dict, List, Tuple

from app.services.chunking.base import Chunk
from app.services.embedding.base import BaseEmbedder
from app.services.vectorstore.base import BaseVectorStore
from app.services.retrieval.base import BaseRetriever

class DenseRetriever(BaseRetriever):
    """Dense retriever using a vector store and embedder."""

    def __init__(self, vectorstore: BaseVectorStore, embedder: BaseEmbedder):
        self.vectorstore = vectorstore
        self.embedder = embedder

    def search(self, query: str, top_k: int) -> List[Tuple[Chunk, float]]:
        return self.vectorstore.search(
            query=query, 
            embedder=self.embedder, 
            top_k=top_k
        )

    def get_config(self) -> Dict[str, Any]:
        return {
            "strategy": "dense",
            "vectorstore": self.vectorstore.get_config() if hasattr(self.vectorstore, "get_config") else None,
            "embedder": self.embedder.get_config() if hasattr(self.embedder, "get_config") else None
        }
