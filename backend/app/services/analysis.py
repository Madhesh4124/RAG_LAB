from typing import List, Dict, Any
import math

class RetrievalAnalyzer:
    """Analyzes the retrieval chunks used to generate an LLM response."""
    
    def __init__(self, chunk_data: List[Any], confidence_threshold: float = 0.5):
        """
        Accepts either a list of dicts parsed from JSON logs, or a list of 
        (Chunk, float) tuples coming directly from the pipeline natively.
        Internally standardizes everything into structured dictionaries predictably.
        """
        self.chunks = []
        self.confidence_threshold = float(confidence_threshold)
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
        
    def has_low_confidence(self) -> bool:
        """Returns True if the highest similarity score is unequivocally below the reliability threshold."""
        ranked = self.get_ranked_chunks()
        if not ranked:
            return True
        return ranked[0].get("score", 0.0) < self.confidence_threshold

    def score_distribution(self) -> Dict[str, float]:
        """Returns basic distribution stats for retrieval similarity scores."""
        if not self.chunks:
            return {"min": 0.0, "max": 0.0, "std": 0.0}

        scores = [float(c.get("score", 0.0)) for c in self.chunks]
        mean = sum(scores) / len(scores)
        variance = sum((score - mean) ** 2 for score in scores) / len(scores)
        return {
            "min": min(scores),
            "max": max(scores),
            "std": math.sqrt(variance),
        }

    def chunk_diversity(self) -> float:
        """Returns a simple diversity ratio using unique first-50-char chunk prefixes."""
        if not self.chunks:
            return 0.0

        prefixes = []
        for chunk in self.chunks:
            prefix = str(chunk.get("text", "")).strip()[:50]
            prefixes.append(prefix)

        unique_prefixes = len(set(prefixes))
        return unique_prefixes / len(prefixes)

    def summary_stats(self) -> Dict[str, Any]:
        """Returns all computed retrieval quality stats in one payload."""
        return {
            "total_chunks_retrieved": len(self.chunks),
            "avg_similarity": self.get_avg_similarity(),
            "score_distribution": self.score_distribution(),
            "chunk_diversity": self.chunk_diversity(),
            "warning_flag": self.has_low_confidence(),
            "confidence_threshold": self.confidence_threshold,
            "top_contributors": self.get_top_contributors(),
            "ranked_chunks": self.get_ranked_chunks(),
        }
