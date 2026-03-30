"""
Sentence-window chunking strategy.

Builds sentence-level chunks for matching, while storing a surrounding
sentence window in metadata for richer generation context.
"""

import re
from typing import Any, Dict, List

from app.services.chunking.base import BaseChunker, Chunk

# Keep sentence splitting aligned with SemanticChunker.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


class SentenceWindowChunker(BaseChunker):
    """Chunker that indexes individual sentences and stores context windows.

    Args:
        window_size: Total number of sentences to include in the context
            window (center sentence plus surrounding neighbors).
    """

    def __init__(self, window_size: int = 3) -> None:
        if window_size <= 0:
            raise ValueError(
                f"window_size must be a positive integer, got {window_size}"
            )
        self.window_size = window_size

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        segments = _SENTENCE_SPLIT_RE.split(text)
        return [s for s in segments if s.strip()]

    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        if not text:
            return []

        sentences = self._split_sentences(text)
        if not sentences:
            return []

        chunks: List[Chunk] = []
        current_idx = 0
        half_window = self.window_size // 2

        for idx, sentence in enumerate(sentences):
            start_idx = text.find(sentence, current_idx)
            if start_idx == -1:
                # Fallback search from start if whitespace normalization shifted.
                start_idx = text.find(sentence)
                if start_idx == -1:
                    continue
            end_idx = start_idx + len(sentence)
            current_idx = end_idx

            window_start = max(0, idx - half_window)
            window_end = min(len(sentences), idx + half_window + 1)
            window_text = " ".join(sentences[window_start:window_end])

            chunk_metadata = metadata.copy()
            chunk_metadata["window_text"] = window_text

            chunks.append(
                Chunk(
                    text=sentence,
                    metadata=chunk_metadata,
                    start_char=start_idx,
                    end_char=end_idx,
                )
            )

        return chunks

    def get_config(self) -> Dict[str, Any]:
        return {
            "strategy": "sentence_window",
            "window_size": self.window_size,
        }
