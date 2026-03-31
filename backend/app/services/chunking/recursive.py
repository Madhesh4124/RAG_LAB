import logging
import re
from typing import Any, Dict, List, Optional
from app.services.chunking.base import BaseChunker, Chunk


logger = logging.getLogger(__name__)


class RecursiveChunker(BaseChunker):
    """
    Splits text using a list of separators recursively, falling back to 
    fixed-size chunking with overlap if necessary.
    """

    def __init__(
        self, 
        chunk_size: int = 512, 
        overlap: int = 50, 
        separators: Optional[List[str]] = None,
        min_chunk_size: int = 50,
        apply_overlap_recursively: bool = False,
        max_recursion_depth: int = 10,
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
        self.separators = separators if separators is not None else ["\n\n", "\n", ". ", " "]
        self.min_chunk_size = min_chunk_size
        self.apply_overlap_recursively = apply_overlap_recursively
        self.max_recursion_depth = max_recursion_depth
        self.debug = debug

    def _log_debug(self, message: str) -> None:
        if self.debug:
            logger.info("[RecursiveChunker] %s", message)

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

        # If text is already small enough (or we reached limits), no need to split further.
        if (
            len(text) <= self.chunk_size
            or len(text) <= self.min_chunk_size
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
                        "end_char": base_offset + end,
                        "separator_used": "fixed_size",
                        "depth": depth,
                    })
                if end == len(text):
                    break
                # Only move forward by chunk_size - overlap to implement overlap
                move_step = max(1, self.chunk_size - self.overlap)
                start += move_step
            return res

        separator = separators[0]
        next_separators = separators[1:]
        self._log_debug(f"Depth={depth}, separator={separator!r}, text_len={len(text)}")

        # If separator is not in text, move to the next separator
        if not separator or separator not in text:
            return self._split_with_offsets(
                text,
                base_offset,
                next_separators,
                depth=depth + 1,
                separator_used=separator_used,
            )

        # Split text by separator while preserving separators in output.
        splits = re.split(f"({re.escape(separator)})", text)
        parts: List[str] = []
        for i in range(0, len(splits), 2):
            part = splits[i]
            if i + 1 < len(splits):
                part += splits[i + 1]
            parts.append(part)

        res = []
        current_offset = base_offset
        self._log_debug(f"Depth={depth}, separator={separator!r}, parts={len(parts)}")

        for s in parts:
            part_start = current_offset
            part_end = current_offset + len(s)

            if s:
                if len(s) > self.chunk_size and len(s) > self.min_chunk_size:
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
            can_merge = (len(prev["text"]) + len(curr["text"])) <= self.chunk_size

            if can_merge and (len(prev["text"]) < self.min_chunk_size or len(curr["text"]) < self.min_chunk_size):
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
        if not chunks:
            return []

        overlapped = [chunks[0].copy()]
        for curr in chunks[1:]:
            curr_copy = curr.copy()
            overlap_start = max(0, curr_copy["start_char"] - self.overlap)
            overlap_prefix = original_text[overlap_start:curr_copy["start_char"]]
            if overlap_prefix:
                curr_copy["text"] = overlap_prefix + curr_copy["text"]
                curr_copy["start_char"] = overlap_start
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
            "debug": self.debug,
        }
