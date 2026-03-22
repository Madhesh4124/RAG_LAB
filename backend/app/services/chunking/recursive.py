from typing import Any, Dict, List
from backend.app.services.chunking.base import BaseChunker, Chunk

class RecursiveChunker(BaseChunker):
    """
    Splits text using a list of separators recursively, falling back to 
    fixed-size chunking with overlap if necessary.
    """

    def __init__(
        self, 
        chunk_size: int = 512, 
        overlap: int = 50, 
        separators: List[str] = None
    ):
        self.chunk_size = chunk_size
        self.overlap = min(overlap, chunk_size - 1) if chunk_size > 1 else 0
        self.separators = separators if separators is not None else ["\n\n", "\n", ". ", " "]

    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        raw_chunks = self._split_with_offsets(text, 0, self.separators)
        chunks = []
        for rc in raw_chunks:
            chunks.append(Chunk(
                text=rc["text"],
                metadata=metadata.copy(),
                start_char=rc["start_char"],
                end_char=rc["end_char"]
            ))
        return chunks

    def _split_with_offsets(self, text: str, base_offset: int, separators: List[str]) -> List[Dict[str, Any]]:
        # If text is already small enough, no need to split further
        if len(text) <= self.chunk_size:
            if text:
                return [{"text": text, "start_char": base_offset, "end_char": base_offset + len(text)}]
            return []

        # If no separators left, fallback to fixed-size chunking
        if not separators:
            res = []
            start = 0
            while start < len(text):
                end = min(start + self.chunk_size, len(text))
                chunk_text = text[start:end]
                if chunk_text:
                    res.append({
                        "text": chunk_text,
                        "start_char": base_offset + start,
                        "end_char": base_offset + end
                    })
                if end == len(text):
                    break
                # Only move forward by chunk_size - overlap to implement overlap
                move_step = max(1, self.chunk_size - self.overlap)
                start += move_step
            return res

        separator = separators[0]
        next_separators = separators[1:]

        # If separator is not in text, move to the next separator
        if not separator or separator not in text:
            return self._split_with_offsets(text, base_offset, next_separators)

        # Split text by separator
        splits = text.split(separator)
        res = []
        current_offset = base_offset

        for i, s in enumerate(splits):
            if s:
                if len(s) > self.chunk_size:
                    # Recursively split large pieces
                    res.extend(self._split_with_offsets(s, current_offset, next_separators))
                else:
                    # Keep small pieces
                    res.append({
                        "text": s,
                        "start_char": current_offset,
                        "end_char": current_offset + len(s)
                    })
            
            # advance offset by the length of the string `s` plus the separator
            current_offset += len(s)
            if i < len(splits) - 1:
                current_offset += len(separator)

        return res

    def get_config(self) -> Dict[str, Any]:
        return {
            "strategy": "recursive",
            "chunk_size": self.chunk_size,
            "overlap": self.overlap,
            "separators": self.separators
        }
