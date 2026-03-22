import re
from typing import Any, Dict, List
from backend.app.services.chunking.base import BaseChunker, Chunk

class RegexChunker(BaseChunker):
    """
    Splits text using a regular expression pattern and filters out chunks 
    that are smaller than min_chunk_size.
    """

    PARAGRAPH_PATTERN = r"\n\n+"
    SENTENCE_PATTERN = r"(?<=[.!?])\s+"
    DIALOGUE_PATTERN = r"\n(?=[A-Z][a-z]+:)"

    def __init__(self, pattern: str, min_chunk_size: int = 100):
        self.pattern = pattern
        self.min_chunk_size = min_chunk_size

    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        # Split text into pieces using the provided regex pattern
        pieces = re.split(self.pattern, text)
        chunks = []
        current_idx = 0
        
        for p in pieces:
            if not p:
                continue
            
            # Locate the start position of this piece in the original text
            start_idx = text.find(p, current_idx)
            if start_idx != -1:
                end_idx = start_idx + len(p)
                
                # Only keep pieces that meet the size requirement
                if len(p) >= self.min_chunk_size:
                    chunks.append(Chunk(
                        text=p,
                        metadata=metadata.copy(),
                        start_char=start_idx,
                        end_char=end_idx
                    ))
                
                # Advance the search index
                current_idx = end_idx

        return chunks

    def get_config(self) -> Dict[str, Any]:
        return {
            "strategy": "regex",
            "pattern": self.pattern,
            "min_chunk_size": self.min_chunk_size
        }
