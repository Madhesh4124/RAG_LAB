"""
Fixed-size chunking strategy.

Splits text into chunks of a fixed character length with a configurable
overlap between consecutive chunks.
"""

import uuid
from typing import Any, Callable, Dict, List

from app.services.chunking.base import BaseChunker, Chunk


class FixedSizeChunker(BaseChunker):
    """Chunker that slides a fixed-size window across the text.

    Each chunk contains exactly ``chunk_size`` units as measured by
    ``length_function`` (the final chunk may be shorter if there is not
    enough remaining text).  Consecutive chunks share ``overlap`` units
    so that context is preserved across boundaries.

    Args:
        chunk_size: Number of length units per chunk.
        overlap: Number of length units shared between consecutive chunks.
        length_function: Callable used to measure text length.  Defaults
            to ``len`` (character count).  Pass a token-counting wrapper
            (e.g. a :pypi:`tiktoken` encoder) for token-aware chunking.

    Raises:
        ValueError: If ``chunk_size`` is not positive or ``overlap`` is
                    negative or greater than or equal to ``chunk_size``.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        overlap: int = 50,
        length_function: Callable[[str], int] = len,
    ) -> None:
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
        self.length_fn = length_function

    # ------------------------------------------------------------------
    # BaseChunker interface
    # ------------------------------------------------------------------

    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        """Split *text* into fixed-size chunks with overlap.

        A sliding window of ``chunk_size`` units advances by
        ``chunk_size - overlap`` units on each step.  The supplied
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
        start = 0

        while start < len(text):
            # Step 1: Heuristic char expansion (~4.5 chars per token on average).
            # This gives a generous upper bound so binary search has room to contract.
            char_guess = int(self.chunk_size * 4.5)
            end = min(start + char_guess, len(text))

            # Step 2: Binary search for the exact token boundary in O(log N).
            low, high = start, end
            while low < high:
                mid = (low + high + 1) // 2  # upper-mid avoids infinite loop
                if self.length_fn(text[start:mid]) <= self.chunk_size:
                    low = mid
                else:
                    high = mid - 1
            end = low

            # Step 3: Guard against empty or stalled chunks.
            if end <= start:
                end = min(start + 1, len(text))

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

            if end >= len(text):
                break

            # Step 4: Advance by (chunk_chars - overlap) characters.
            # Overlap is intentionally character-based for performance;
            # token-perfect overlap would require a second binary search per step.
            step = max(1, (end - start) - self.overlap)
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
            "length_function": getattr(self.length_fn, "__name__", repr(self.length_fn)),
        }
