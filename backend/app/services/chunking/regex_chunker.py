import re
from typing import Any, Callable, Dict, List, Tuple
from app.services.chunking.base import BaseChunker, Chunk


class RegexChunker(BaseChunker):
    """
    Splits text using a regular expression pattern.

    The pattern is used as a *delimiter* — the text between consecutive
    matches becomes a piece.  Pieces that are shorter than
    ``min_chunk_size`` characters are **merged** into the next piece
    rather than discarded, so no content is lost.

    Offsets are derived from ``re.finditer`` match spans for accuracy,
    avoiding the fragile ``str.find`` approach that can produce wrong
    positions when the same sub-string appears multiple times.
    """

    # Convenience class-level patterns callers can reference.
    PARAGRAPH_PATTERN = r"\n\n+"
    SENTENCE_PATTERN = r"(?<=[.!?])\s+"
    DIALOGUE_PATTERN = r"\n(?=[A-Z][a-z]+:)"

    def __init__(self, pattern: str, min_chunk_size: int = 100, length_function: Callable[[str], int] = len) -> None:
        if not pattern:
            raise ValueError("pattern must be a non-empty string")
        if min_chunk_size < 0:
            raise ValueError("min_chunk_size must be non-negative")
        self.pattern = pattern
        self.min_chunk_size = min_chunk_size
        self.length_fn = length_function

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _split_with_offsets(self, text: str) -> List[Tuple[str, int, int]]:
        """Return (piece_text, start_char, end_char) tuples using match spans.

        Works by iterating over delimiter matches and computing the gaps
        between them, which are the actual pieces of content.
        """
        pieces: List[Tuple[str, int, int]] = []
        prev_end = 0

        for match in re.finditer(self.pattern, text):
            piece = text[prev_end : match.start()]
            if piece:  # skip empty strings caused by leading/trailing delimiters
                pieces.append((piece, prev_end, match.start()))
            prev_end = match.end()

        # Trailing piece after the last delimiter (or the entire text when
        # the pattern never matches).
        tail = text[prev_end:]
        if tail:
            pieces.append((tail, prev_end, len(text)))

        return pieces

    # ------------------------------------------------------------------
    # BaseChunker interface
    # ------------------------------------------------------------------

    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        """Split *text* by the regex pattern and return Chunk objects.

        Pieces shorter than ``min_chunk_size`` are accumulated into a
        buffer and prepended to the next qualifying piece so that no
        content is silently lost.

        Args:
            text: The full text to be chunked.
            metadata: A dictionary of metadata to attach to each chunk.

        Returns:
            A list of Chunk objects.  Returns an empty list when *text*
            is empty or the pattern produces no usable pieces.
        """
        if not text:
            return []

        raw_pieces = self._split_with_offsets(text)
        if not raw_pieces:
            return []

        chunks: List[Chunk] = []
        buffer_text = ""
        buffer_start = 0  # start_char of the first buffered piece

        for piece_text, start, end in raw_pieces:
            if not buffer_text:
                # Start a fresh buffer with this piece.
                buffer_text = piece_text
                buffer_start = start
            else:
                # Append to existing buffer, bridging the gap from the
                # original text so offsets remain correct.
                buffer_text = text[buffer_start:end]

            if self.length_fn(buffer_text) >= self.min_chunk_size:
                chunks.append(
                    Chunk(
                        text=buffer_text,
                        metadata=metadata.copy(),
                        start_char=buffer_start,
                        end_char=buffer_start + len(buffer_text),
                    )
                )
                buffer_text = ""
                buffer_start = end

        # Flush any remaining buffered text (even if < min_chunk_size) so
        # that no content is lost.
        if buffer_text:
            chunks.append(
                Chunk(
                    text=buffer_text,
                    metadata=metadata.copy(),
                    start_char=buffer_start,
                    end_char=buffer_start + len(buffer_text),
                )
            )

        return chunks

    def get_config(self) -> Dict[str, Any]:
        return {
            "strategy": "regex",
            "pattern": self.pattern,
            "min_chunk_size": self.min_chunk_size,
            "length_function": getattr(self.length_fn, "__name__", repr(self.length_fn)),
        }
