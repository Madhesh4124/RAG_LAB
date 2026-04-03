"""MMR Retriever implementation."""

from typing import Any, Dict, List, Tuple
import numpy as np

from app.services.chunking.base import Chunk
from app.services.retrieval.base import BaseRetriever
from app.services.retrieval.dense_retriever import DenseRetriever

class MMRRetriever(BaseRetriever):
    """MMR retriever wrapping a dense retriever."""

    def __init__(self, dense_retriever: DenseRetriever, lambda_mult: float = 0.5):
        self.dense_retriever = dense_retriever
        self.lambda_mult = lambda_mult

    def search(self, query: str, top_k: int) -> List[Tuple[Chunk, float]]:
        # Retrieve top_k * 4 candidates from dense retriever
        candidates = self.dense_retriever.search(query, top_k=top_k * 4)
        
        if not candidates:
            return []
            
        # Extract embeddings for candidates
        texts = [chunk.text if hasattr(chunk, "text") else getattr(chunk, "page_content", str(chunk)) for chunk, _ in candidates]
        
        embedder = self.dense_retriever.embedder
        chunk_embs = np.array(embedder.embed_batch(texts))
        
        # Precompute original relevance query similarities (we use the dense retriever's provided scores)
        query_sims = np.array([score for _, score in candidates])
        
        def cosine_sim(v_target, m_selected):
            dot_products = np.dot(m_selected, v_target)
            norms_selected = np.linalg.norm(m_selected, axis=1)
            norm_target = np.linalg.norm(v_target)
            denominators = norms_selected * norm_target
            denominators[denominators == 0] = 1e-10
            return dot_products / denominators
        
        selected_indices = []
        unselected_indices = list(range(len(candidates)))
        selected_results = []
        
        if unselected_indices:
            best_idx = int(np.argmax(query_sims))
            selected_indices.append(best_idx)
            unselected_indices.remove(best_idx)
            # Initial item has no diversity penalty
            first_score = float(self.lambda_mult * query_sims[best_idx])
            selected_results.append((candidates[best_idx][0], first_score))
            
        while len(selected_indices) < top_k and unselected_indices:
            best_score = -float("inf")
            best_idx = -1
            
            sel_embs = chunk_embs[selected_indices]
            
            for idx in unselected_indices:
                relevance = query_sims[idx]
                candidate_emb = chunk_embs[idx]
                
                similarities = cosine_sim(candidate_emb, sel_embs)
                diversity_penalty = np.max(similarities) if len(similarities) > 0 else 0.0
                
                mmr_score = self.lambda_mult * relevance - (1 - self.lambda_mult) * diversity_penalty
                
                if mmr_score > best_score:
                    best_score = float(mmr_score)
                    best_idx = idx
            
            selected_indices.append(best_idx)
            unselected_indices.remove(best_idx)
            selected_results.append((candidates[best_idx][0], best_score))
            
        return selected_results

    def get_config(self) -> Dict[str, Any]:
        return {
            "strategy": "mmr",
            "lambda_mult": self.lambda_mult,
            "dense_retriever": self.dense_retriever.get_config() if hasattr(self.dense_retriever, "get_config") else None
        }
