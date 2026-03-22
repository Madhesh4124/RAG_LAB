"""
Fixed-size chunking strategy.

Splits text into chunks of a fixed character length with a configurable
overlap between consecutive chunks.
"""

import uuid
from typing import Any, Dict, List

from backend.app.services.chunking.base import BaseChunker, Chunk


class FixedSizeChunker(BaseChunker):
    """Chunker that slides a fixed-size window across the text.

    Each chunk contains exactly `chunk_size` characters (the final chunk
    may be shorter if there is not enough remaining text).  Consecutive
    chunks share `overlap` characters so that context is preserved
    across boundaries.

    Args:
        chunk_size: Number of characters per chunk.
        overlap: Number of characters shared between consecutive chunks.

    Raises:
        ValueError: If `chunk_size` is not positive or `overlap` is
                    negative or greater than or equal to `chunk_size`.
    """

    def __init__(self, chunk_size: int = 512, overlap: int = 50) -> None:
        if chunk_size <= 0:
            raise ValueError(
                f"chunk_size must be a positive integer, got {chunk_size}"
            )
        if overlap < 0:
            raise ValueError(
                f"overlap must be non-negative, got {overlap}"
            )
        if overlap >= chunk_size:
            raise ValueError(
                f"overlap ({overlap}) must be less than "
                f"chunk_size ({chunk_size})"
            )

        self.chunk_size = chunk_size
        self.overlap = overlap

    # ------------------------------------------------------------------
    # BaseChunker interface
    # ------------------------------------------------------------------

    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        """Split *text* into fixed-size chunks with overlap.

        A sliding window of `chunk_size` characters advances by
        `chunk_size - overlap` characters on each step.  The supplied
        *metadata* is copied into every resulting chunk.

        Args:
            text: The full text to be chunked.
            metadata: A dictionary of metadata to attach to each
                      generated chunk.

        Returns:
            A list of Chunk objects.  Returns an empty list when
            *text* is empty.
        """
        if not text:
            return []

        chunks: List[Chunk] = []
        step = self.chunk_size - self.overlap
        start = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]

            chunks.append(
                Chunk(
                    id=uuid.uuid4(),
                    text=chunk_text,
                    metadata=metadata.copy(),
                    start_char=start,
                    end_char=end,
                )
            )

            # Advance the window
            start += step

        return chunks

    def get_config(self) -> Dict[str, Any]:
        """Return the chunker's current configuration.

        Returns:
            A dict with the strategy name, chunk size, and overlap.
        """
        return {
            "strategy": "fixed_size",
            "chunk_size": self.chunk_size,
            "overlap": self.overlap,
        }
