"""Sparse BM25 Retriever implementation."""

from typing import Any, Dict, List, Tuple
from rank_bm25 import BM25Okapi

from backend.app.services.chunking.base import Chunk
from backend.app.services.retrieval.base import BaseRetriever

class BM25Retriever(BaseRetriever):
    """BM25 sparse retriever."""

    def __init__(self, chunks: List[Chunk]):
        self.chunks = chunks
        
        # Tokenize by splitting on whitespace
        tokenized_corpus = [chunk.text.split() for chunk in self.chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, top_k: int) -> List[Tuple[Chunk, float]]:
        tokenized_query = query.split()
        scores = self.bm25.get_scores(tokenized_query)
        
        max_score = max(scores) if len(scores) > 0 else 0.0
        
        if max_score == 0.0:
            return []
            
        # Pair chunks with scores
        chunk_scores = list(zip(self.chunks, scores))
        
        # Sort by score descending
        chunk_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Normalize scores in 0-1 range and limit to top_k
        results = []
        for chunk, score in chunk_scores[:top_k]:
            normalized_score = score / max_score
            results.append((chunk, normalized_score))
            
        return results

    def get_config(self) -> Dict[str, Any]:
        return {"strategy": "bm25"}
