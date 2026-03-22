"""
Semantic chunking strategy.

Splits text at natural sentence boundaries (periods, newlines) and
groups sentences together until a size threshold is reached, then
starts a new chunk.
"""

import re
import uuid
from typing import Any, Dict, List

from backend.app.services.chunking.base import BaseChunker, Chunk

# Regex that splits on sentence-ending punctuation (.!?) followed by
# whitespace, or on newline characters — while keeping the delimiter
# attached to the preceding sentence.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


class SemanticChunker(BaseChunker):
    """Chunker that splits text at sentence boundaries.

    Instead of cutting at fixed character positions, this chunker first
    breaks the text into sentences (splitting on periods, exclamation
    marks, question marks followed by whitespace, and newline
    characters).  Sentences are then grouped together sequentially
    until adding the next sentence would exceed `max_chunk_size`
    characters, at which point a new chunk is started.

    Args:
        max_chunk_size: Maximum number of characters allowed in a
                        single chunk.

    Raises:
        ValueError: If `max_chunk_size` is not positive.
    """

    def __init__(self, max_chunk_size: int = 512) -> None:
        if max_chunk_size <= 0:
            raise ValueError(
                f"max_chunk_size must be a positive integer, got {max_chunk_size}"
            )
        self.max_chunk_size = max_chunk_size

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split *text* into sentence-level segments.

        Splits on sentence-ending punctuation (.!?) followed by
        whitespace, as well as newline characters.  Empty segments
        are discarded.

        Returns:
            A list of non-empty sentence strings.
        """
        segments = _SENTENCE_SPLIT_RE.split(text)
        return [s for s in segments if s.strip()]

    # ------------------------------------------------------------------
    # BaseChunker interface
    # ------------------------------------------------------------------

    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        """Split *text* into semantically meaningful chunks.

        Sentences are accumulated into a chunk until the next sentence
        would push the chunk beyond `max_chunk_size` characters.  A
        single sentence that exceeds `max_chunk_size` on its own is
        placed into its own chunk (it will *not* be truncated).

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

        sentences = self._split_sentences(text)
        if not sentences:
            return []

        chunks: List[Chunk] = []
        current_sentences: List[str] = []
        current_length = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            # If adding this sentence (plus a separating space) exceeds
            # the threshold, finalise the current chunk first.
            would_be_length = (
                current_length + (1 if current_sentences else 0) + sentence_len
            )

            if current_sentences and would_be_length > self.max_chunk_size:
                # Flush the accumulated sentences as a chunk.
                chunk_text = " ".join(current_sentences)
                start_char = text.index(current_sentences[0])
                end_char = start_char + len(chunk_text)

                chunks.append(
                    Chunk(
                        id=uuid.uuid4(),
                        text=chunk_text,
                        metadata=metadata.copy(),
                        start_char=start_char,
                        end_char=end_char,
                    )
                )

                current_sentences = []
                current_length = 0

            current_sentences.append(sentence)
            current_length += (1 if current_length > 0 else 0) + sentence_len

        # Flush any remaining sentences.
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            start_char = text.index(current_sentences[0])
            end_char = start_char + len(chunk_text)

            chunks.append(
                Chunk(
                    id=uuid.uuid4(),
                    text=chunk_text,
                    metadata=metadata.copy(),
                    start_char=start_char,
                    end_char=end_char,
                )
            )

        return chunks

    def get_config(self) -> Dict[str, Any]:
        """Return the chunker's current configuration.

        Returns:
            A dict with the strategy name and max chunk size.
        """
        return {
            "strategy": "semantic",
            "max_chunk_size": self.max_chunk_size,
        }
