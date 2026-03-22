from typing import List, Tuple, Dict, Any

class RetrievalAnalyzer:
    """Analyzes the retrieval chunks used to generate an LLM response."""
    
    def __init__(self, chunk_data: List[Any]):
        """
        Accepts either a list of dicts parsed from JSON logs, or a list of 
        (Chunk, float) tuples coming directly from the pipeline natively.
        Internally standardizes everything into structured dictionaries predictably.
        """
        self.chunks = []
        for item in chunk_data:
            if isinstance(item, tuple) and len(item) == 2:
                # Assuming (Chunk, score) format mapped linearly
                chunk, score = item
                self.chunks.append({
                    "id": getattr(chunk, "id", None) or str(chunk),
                    "text": getattr(chunk, "text", str(chunk)),
                    "score": float(score)
                })
            elif isinstance(item, dict):
                # Standard deserialization logic mapped natively out of Postgres 
                self.chunks.append(item)
            else:
                self.chunks.append({"text": str(item), "score": 0.0})
                
    def get_ranked_chunks(self) -> List[Dict[str, Any]]:
        """Returns chunks sorted by similarity score highest to lowest."""
        return sorted(self.chunks, key=lambda c: c.get("score", 0.0), reverse=True)
        
    def get_top_contributors(self) -> List[Dict[str, Any]]:
        """Returns the top 3 chunks that most influenced the answer."""
        return self.get_ranked_chunks()[:3]
        
    def get_avg_similarity(self) -> float:
        """Returns the mean similarity score across all retrieved chunks."""
        if not self.chunks:
            return 0.0
        total = sum(c.get("score", 0.0) for c in self.chunks)
        return total / len(self.chunks)
        
    def has_low_confidence(self, threshold: float = 0.5) -> bool:
        """Returns True if the highest similarity score is unequivocally below the reliability threshold."""
        ranked = self.get_ranked_chunks()
        if not ranked:
            return True
        return ranked[0].get("score", 0.0) < threshold
