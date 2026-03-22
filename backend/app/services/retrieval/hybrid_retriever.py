"""Hybrid Retriever combining Dense and Sparse retrievers using RRF."""

from typing import Any, Dict, List, Tuple

from app.services.chunking.base import Chunk
from app.services.retrieval.base import BaseRetriever
from app.services.retrieval.dense_retriever import DenseRetriever
from app.services.retrieval.sparse_retriever import BM25Retriever

class HybridRetriever(BaseRetriever):
    """Hybrid Retriever running dense and sparse retrieval and merging them."""

    def __init__(self, dense_retriever: DenseRetriever, sparse_retriever: BM25Retriever, alpha: float = 0.7):
        self.dense_retriever = dense_retriever
        self.sparse_retriever = sparse_retriever
        self.alpha = alpha

    def search(self, query: str, top_k: int) -> List[Tuple[Chunk, float]]:
        dense_results = self.dense_retriever.search(query, top_k)
        
        # Only use sparse if it has chunks indexed
        if len(self.sparse_retriever.chunks) == 0:
            return dense_results
            
        sparse_results = self.sparse_retriever.search(query, top_k)

        # Build dictionaries for fast lookup by chunk ID
        dense_dict = {chunk.id: (chunk, score) for chunk, score in dense_results}
        sparse_dict = {chunk.id: (chunk, score) for chunk, score in sparse_results}

        # Deduplicate chunks
        all_chunk_ids = set(dense_dict.keys()).union(set(sparse_dict.keys()))

        merged_results = []
        for chunk_id in all_chunk_ids:
            chunk = dense_dict[chunk_id][0] if chunk_id in dense_dict else sparse_dict[chunk_id][0]
            
            dense_score = dense_dict.get(chunk_id, (None, 0.0))[1]
            sparse_score = sparse_dict.get(chunk_id, (None, 0.0))[1]

            combined_score = self.alpha * dense_score + (1.0 - self.alpha) * sparse_score
            merged_results.append((chunk, combined_score))

        # Sort combined results descending
        merged_results.sort(key=lambda x: x[1], reverse=True)

        return merged_results[:top_k]

    def get_config(self) -> Dict[str, Any]:
        return {
            "strategy": "hybrid",
            "alpha": self.alpha,
            "dense_retriever": self.dense_retriever.get_config() if hasattr(self.dense_retriever, "get_config") else {},
            "sparse_retriever": self.sparse_retriever.get_config() if hasattr(self.sparse_retriever, "get_config") else {},
        }
