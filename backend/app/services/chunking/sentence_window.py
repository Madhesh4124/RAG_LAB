"""
Sentence-window chunking strategy.

Builds sentence-level chunks for matching, while storing a surrounding
sentence window in metadata for richer generation context.
"""

import copy
import logging
import os
import re
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.services.chunking.base import BaseChunker, Chunk

# Keep sentence splitting aligned with SemanticChunker (split on paragraph boundaries).
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n\n+")
logger = logging.getLogger(__name__)


class SentenceWindowChunker(BaseChunker):
    """Chunker that indexes individual sentences and stores context windows.

    Each sentence becomes its own retrievable chunk.  A surrounding window
    of ``window_size`` sentences (the centre sentence plus its neighbours)
    is stored in ``chunk.metadata["window_text"]`` for richer generation
    context.

    Args:
        window_size: Total number of sentences to include in the context
            window (centre sentence plus surrounding neighbours).  Both
            odd and even values are supported — the centre sentence always
            occupies exactly one slot.
        length_function: Callable used to measure text length.  Defaults
            to ``len`` (character count).  Pass a token-counting wrapper
            (e.g. a :pypi:`tiktoken` encoder) for token-aware windowing.
        max_chunk_size: Optional sentence-size limit. Values above 150 are
            hard-capped at 150.
    """

    def __init__(
        self,
        window_size: int = 3,
        length_function: Callable[[str], int] = len,
        max_chunk_size: Optional[int] = None,
        fallback_chunker: Optional[BaseChunker] = None,
    ) -> None:
        if window_size <= 0:
            raise ValueError(
                f"window_size must be a positive integer, got {window_size}"
            )
        if max_chunk_size is not None and max_chunk_size <= 0:
            raise ValueError("max_chunk_size must be positive when provided")

        self.window_size = window_size
        self.length_fn = length_function
        # Sentence-window chunks are hard-capped at 150 units.
        self.max_chunk_size = min(max_chunk_size or 150, 150)
        self.fallback_chunker = fallback_chunker

    def _resolve_fallback_chunker(self) -> BaseChunker:
        from app.services.chunking.fixed_size import FixedSizeChunker
        if self.fallback_chunker is not None:
            return self.fallback_chunker

        size = self.max_chunk_size or 512
        overlap = min(50, max(0, size // 10))
        return FixedSizeChunker(
            chunk_size=size,
            overlap=overlap,
            length_function=self.length_fn
        )

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        segments = _SENTENCE_SPLIT_RE.split(text)
        sentences = [s for s in segments if s.strip()]
        
        # Sub-split segments that are too long to prevent memory blow-up.
        max_segment_chars = int(os.getenv("SENTENCE_WINDOW_MAX_SEGMENT_CHARS", "2000"))
        final_sentences = []
        for s in sentences:
            if len(s) > max_segment_chars:
                for i in range(0, len(s), max_segment_chars):
                    piece = s[i : i + max_segment_chars]
                    if piece.strip():
                        final_sentences.append(piece)
            else:
                final_sentences.append(s)
        return final_sentences

    @staticmethod
    def _find_sentence_span(
        text: str,
        sentence: str,
        search_from: int,
    ) -> Optional[Tuple[int, int]]:
        """Locate *sentence* in *text* at or after *search_from*.

        Uses a forward regex search that treats any run of whitespace as
        equivalent to a single space in the sentence pattern.  This avoids
        both the repeated-sentence bug (grabbing the first occurrence in
        the document) and the whitespace-drift bug (hard failing when the
        split regex consumed normalised whitespace).

        Returns:
            ``(start, end)`` absolute character offsets, or ``None`` if the
            sentence cannot be located.
        """
        # Build a pattern that flexibly matches whitespace inside the sentence
        # so that multi-space / tab gaps don't cause a miss.
        escaped = re.escape(sentence)
        flexible = escaped.replace(r"\ ", r"\s+")
        pattern = re.compile(flexible)

        m = pattern.search(text, search_from)
        if m:
            return m.start(), m.end()

        # Last-resort: strict forward scan without whitespace flexibility.
        idx = text.find(sentence, search_from)
        if idx != -1:
            return idx, idx + len(sentence)

        return None

    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        """Split *text* into per-sentence chunks with surrounding context.

        Args:
            text: The full text to be chunked.
            metadata: A dictionary of metadata to attach to each chunk.
                Each chunk receives a copy enriched with ``window_text``.

        Returns:
            A list of Chunk objects, one per detected sentence.  Returns
            an empty list when *text* is empty or no sentences are found.
        """
        if not text:
            return []

        sentences = self._split_sentences(text)
        if not sentences:
            return []

        chunks: List[Chunk] = []
        cursor = 0
        spans: List[Optional[Tuple[int, int]]] = []
        for sentence in sentences:
            span = self._find_sentence_span(text, sentence, cursor)
            spans.append(span)
            if span:
                cursor = span[1]

        for idx, sentence in enumerate(sentences):
            span = spans[idx]
            if span is None:
                # Sentence not found even with flexible search; skip.
                logger.warning("Could not locate sentence span for: %r", sentence[:120])
                continue
            start_idx, end_idx = span

            # Compute left/right reach independently so the centre sentence
            # always occupies exactly one slot and the total window size
            # equals self.window_size for both odd and even values.
            left = self.window_size // 2
            right = self.window_size - left - 1  # reserves 1 slot for the centre
            window_start = max(0, idx - left)
            window_end = min(len(sentences) - 1, idx + right)

            # Extract window_text using spans to avoid whitespace drift
            w_start_span = None
            for i in range(window_start, window_end + 1):
                if spans[i] is not None:
                    w_start_span = spans[i][0]
                    break
                    
            w_end_span = None
            for i in range(window_end, window_start - 1, -1):
                if spans[i] is not None:
                    w_end_span = spans[i][1]
                    break
                    
            if w_start_span is not None and w_end_span is not None:
                window_text = text[w_start_span:w_end_span]
            else:
                window_text = sentence

            chunk_metadata = copy.deepcopy(metadata)
            chunk_metadata["window_text"] = window_text

            if self.max_chunk_size and self.length_fn(sentence) > self.max_chunk_size:
                fallback = self._resolve_fallback_chunker()
                # Chunk the single run-on sentence
                sub_chunks = fallback.chunk(sentence, chunk_metadata)

                # The fallback chunker returns local offsets (0 to len(sentence)).
                # We must shift them by start_idx to make them absolute to the document.
                for sc in sub_chunks:
                    sc.start_char += start_idx
                    sc.end_char += start_idx
                    chunks.append(sc)
            else:
                chunks.append(
                    Chunk(
                        id=uuid.uuid4(),
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
            "max_chunk_size": self.max_chunk_size,
            "fallback_chunker": (
                self.fallback_chunker.__class__.__name__
                if self.fallback_chunker is not None
                else None
            ),
            "length_function": getattr(self.length_fn, "__name__", repr(self.length_fn)),
        }
