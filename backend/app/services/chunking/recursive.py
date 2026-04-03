import logging
import re
from typing import Any, Callable, Dict, List, Optional
from app.services.chunking.base import BaseChunker, Chunk


logger = logging.getLogger(__name__)

# Default separators ordered from coarsest to finest.  The sentence-ending
# separator uses a regex lookbehind so splits on ".", "!", and "?" are all
# handled — unlike the naïve ". " string that was used before.
_DEFAULT_SEPARATORS: List[str] = [
    "\n\n",               # paragraph break
    "\n",                 # line break
    r"(?<=[.!?])\s+",    # sentence boundary (all terminal punctuation)
    " ",                  # word boundary (last resort before fixed-size)
]


class RecursiveChunker(BaseChunker):
    """
    Splits text using a list of separators recursively, falling back to
    fixed-size chunking with overlap if necessary.

    Separators are tried from the first element to the last.  If splitting
    on the current separator produces a piece that is still too large, the
    next separator is tried on that piece.  Once all separators are
    exhausted the text is split by fixed-size sliding window.

    Separator strings may be plain strings *or* regex patterns.  The
    ``_split_with_offsets`` method detects regex-special patterns and
    switches between ``re.split`` and plain ``str.split`` accordingly.

    Args:
        chunk_size: Maximum length of a chunk as measured by
            ``length_function``.
        overlap: Number of characters to prepend from the previous chunk
            boundary.  The overlap is "snapped" to the nearest whitespace
            so that words are never cut in half.
        separators: Ordered list of separator strings / regex patterns.
            Defaults to ``[\\n\\n, \\n, r"(?<=[.!?])\\s+", " "]``.
        min_chunk_size: Minimum chunk length.  Pieces below this are
            merged with their neighbour before overlap is applied.
        apply_overlap_recursively: When ``True`` (default), the overlap
            prefix is prepended to every chunk after the first.
        max_recursion_depth: Guard against pathological inputs.
        length_function: Callable used to measure text length.  Defaults
            to ``len`` (character count).  Pass a token-counting wrapper
            for token-aware chunking.
        debug: Emit verbose debug logs.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        overlap: int = 50,
        separators: Optional[List[str]] = None,
        min_chunk_size: int = 100,
        apply_overlap_recursively: bool = True,
        max_recursion_depth: int = 10,
        length_function: Callable[[str], int] = len,
        debug: bool = False,
    ):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0:
            raise ValueError("overlap must be non-negative")
        if min_chunk_size <= 0:
            raise ValueError("min_chunk_size must be positive")
        if max_recursion_depth <= 0:
            raise ValueError("max_recursion_depth must be positive")

        self.chunk_size = chunk_size
        self.overlap = min(overlap, chunk_size - 1) if chunk_size > 1 else 0
        self.separators = separators if separators is not None else _DEFAULT_SEPARATORS
        self.min_chunk_size = min_chunk_size
        self.apply_overlap_recursively = apply_overlap_recursively
        self.max_recursion_depth = max_recursion_depth
        self.length_fn = length_function
        self.debug = debug

    def _log_debug(self, message: str) -> None:
        if self.debug:
            logger.info("[RecursiveChunker] %s", message)

    # ------------------------------------------------------------------
    # Separator helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_regex(pattern: str) -> bool:
        """Return True if *pattern* contains regex-special constructs."""
        # Lookbehinds, quantifiers, character classes, anchors etc.
        return bool(re.search(r"[\\^$.*+?{}()\[\]|]", pattern))

    def _separator_in_text(self, separator: str, text: str) -> bool:
        """Check whether *separator* (plain or regex) is present in *text*."""
        if self._is_regex(separator):
            return bool(re.search(separator, text))
        return separator in text

    def _split_by_separator(self, separator: str, text: str) -> List[str]:
        """Split *text* by *separator* while keeping the separator attached
        to the preceding segment (consistent with the original behaviour).

        For regex separators the pattern is wrapped in a capturing group so
        that ``re.split`` includes the delimiters.  For plain separators the
        same trick is applied via ``re.escape``.
        """
        if self._is_regex(separator):
            # Wrap in a capturing group to keep the delimiter.
            splits = re.split(f"({separator})", text)
        else:
            splits = re.split(f"({re.escape(separator)})", text)

        parts: List[str] = []
        for i in range(0, len(splits), 2):
            part = splits[i]
            if i + 1 < len(splits):
                part += splits[i + 1]
            parts.append(part)
        return parts

    # ------------------------------------------------------------------
    # Main interface
    # ------------------------------------------------------------------

    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        if not text:
            return []

        raw_chunks = self._split_with_offsets(text, 0, self.separators, depth=0, separator_used=None)
        raw_chunks = self._merge_small_chunks(raw_chunks)

        if self.apply_overlap_recursively and self.overlap > 0:
            raw_chunks = self._apply_recursive_overlap(raw_chunks, text)

        chunks = []
        for i, rc in enumerate(raw_chunks):
            if not rc["text"] or not rc["text"].strip():
                continue

            chunk_metadata = metadata.copy()
            chunk_metadata["split_type"] = "recursive"
            chunk_metadata["separator_used"] = rc.get("separator_used")
            chunk_metadata["recursion_depth"] = rc.get("depth", 0)
            chunk_metadata["chunk_index"] = i

            chunks.append(Chunk(
                text=rc["text"],
                metadata=chunk_metadata,
                start_char=rc["start_char"],
                end_char=rc["end_char"]
            ))
        return chunks

    def _split_with_offsets(
        self,
        text: str,
        base_offset: int,
        separators: List[str],
        depth: int,
        separator_used: Optional[str],
    ) -> List[Dict[str, Any]]:
        if not text:
            return []

        text_len = self.length_fn(text)

        # If text is already small enough (or we reached limits), no need to split further.
        if (
            text_len <= self.chunk_size
            or text_len <= self.min_chunk_size
            or depth >= self.max_recursion_depth
        ):
            if text:
                return [{
                    "text": text,
                    "start_char": base_offset,
                    "end_char": base_offset + len(text),
                    "separator_used": separator_used,
                    "depth": depth,
                }]
            return []

        # If no separators left, fallback to token-aware fixed-size chunking.
        if not separators:
            res = []
            start = 0
            while start < len(text):
                # Heuristic char expansion (~4.5 chars/token) gives the binary
                # search an upper bound with room to contract.
                char_guess = int(self.chunk_size * 4.5)
                end = min(start + char_guess, len(text))

                # Binary search for exact token boundary in O(log N).
                low, high = start, end
                while low < high:
                    mid = (low + high + 1) // 2
                    if self.length_fn(text[start:mid]) <= self.chunk_size:
                        low = mid
                    else:
                        high = mid - 1
                end = low

                # Guard against stalled progress.
                if end <= start:
                    end = min(start + 1, len(text))

                chunk_text = text[start:end]
                if chunk_text:
                    res.append({
                        "text": chunk_text,
                        "start_char": base_offset + start,
                        "end_char": base_offset + end,
                        "separator_used": "fixed_size",
                        "depth": depth,
                    })

                if end >= len(text):
                    break
                # Overlap is character-based for performance.
                move_step = max(1, (end - start) - self.overlap)
                start += move_step
            return res

        separator = separators[0]
        next_separators = separators[1:]
        self._log_debug(f"Depth={depth}, separator={separator!r}, text_len={text_len}")

        # If separator is not in text, move to the next separator
        if not separator or not self._separator_in_text(separator, text):
            return self._split_with_offsets(
                text,
                base_offset,
                next_separators,
                depth=depth + 1,
                separator_used=separator_used,
            )

        # Split text by separator while preserving separators in output.
        parts = self._split_by_separator(separator, text)

        res = []
        current_offset = base_offset
        self._log_debug(f"Depth={depth}, separator={separator!r}, parts={len(parts)}")

        for s in parts:
            part_start = current_offset
            part_end = current_offset + len(s)

            if s:
                if self.length_fn(s) > self.chunk_size and self.length_fn(s) > self.min_chunk_size:
                    # Recursively split large pieces
                    res.extend(
                        self._split_with_offsets(
                            s,
                            current_offset,
                            next_separators,
                            depth=depth + 1,
                            separator_used=separator,
                        )
                    )
                else:
                    # Keep small pieces
                    res.append({
                        "text": s,
                        "start_char": part_start,
                        "end_char": part_end,
                        "separator_used": separator,
                        "depth": depth,
                    })

            current_offset = part_end

        return res

    def _merge_small_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not chunks:
            return []

        merged: List[Dict[str, Any]] = [chunks[0].copy()]

        for curr in chunks[1:]:
            prev = merged[-1]
            can_merge = (self.length_fn(prev["text"]) + self.length_fn(curr["text"])) <= self.chunk_size

            # Merge any two consecutive chunks whose combined length still fits
            # within chunk_size.  This avoids leaving unnecessary small fragments
            # when splitting on high-level separators (e.g. \n\n) produces many
            # medium-sized pieces.
            if can_merge:
                prev["text"] = prev["text"] + curr["text"]
                prev["end_char"] = curr["end_char"]
                prev["separator_used"] = curr.get("separator_used") or prev.get("separator_used")
                prev["depth"] = max(prev.get("depth", 0), curr.get("depth", 0))
            else:
                merged.append(curr.copy())

        return [c for c in merged if c["text"] and c["text"].strip()]

    def _apply_recursive_overlap(
        self,
        chunks: List[Dict[str, Any]],
        original_text: str,
    ) -> List[Dict[str, Any]]:
        """Prepend an overlap prefix to every chunk after the first.

        The raw overlap start position is snapped *forward* to the next
        whitespace boundary so that words are never sliced in half.
        """
        if not chunks:
            return []

        overlapped = [chunks[0].copy()]
        for curr in chunks[1:]:
            curr_copy = curr.copy()
            raw_overlap_start = max(0, curr_copy["start_char"] - self.overlap)

            # Snap forward to the nearest whitespace so we never cut a word.
            snap_start = raw_overlap_start
            while snap_start < curr_copy["start_char"] and not original_text[snap_start].isspace():
                snap_start += 1
            # If we snapped all the way to the chunk boundary, fall back to
            # the raw position (better to have a partial word than no overlap).
            if snap_start >= curr_copy["start_char"]:
                snap_start = raw_overlap_start

            overlap_prefix = original_text[snap_start:curr_copy["start_char"]]
            if overlap_prefix:
                curr_copy["text"] = overlap_prefix + curr_copy["text"]
                curr_copy["start_char"] = snap_start
            overlapped.append(curr_copy)

        return overlapped

    def get_config(self) -> Dict[str, Any]:
        return {
            "strategy": "recursive",
            "chunk_size": self.chunk_size,
            "overlap": self.overlap,
            "separators": self.separators,
            "min_chunk_size": self.min_chunk_size,
            "apply_overlap_recursively": self.apply_overlap_recursively,
            "max_recursion_depth": self.max_recursion_depth,
            "length_function": getattr(self.length_fn, "__name__", repr(self.length_fn)),
            "debug": self.debug,
        }
