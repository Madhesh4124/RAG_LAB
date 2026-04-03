"""
Chapter-based chunking strategy.

Splits text at detected chapter or section headings so that each
chapter / section becomes its own chunk.
"""

import logging
import re
import uuid
from typing import Any, Callable, Dict, List, Optional, Pattern, Tuple

from app.services.chunking.base import BaseChunker, Chunk
from app.services.chunking.fixed_size import FixedSizeChunker

# Default heading patterns (case-insensitive, matched at line start):
#   • "Chapter 1", "Chapter IV", "Chapter One" …
#   • Markdown headings: "# …", "## …", "### …"
#   • "PART ONE", "PART 1", "PART IV" …
#   • "Section 1", "Section 1.2" …
#   • A line written entirely in UPPER-CASE (≥4 chars, common in
#     plain-text books for chapter titles)
_DEFAULT_HEADING_PATTERNS: List[str] = [
    r"^chapter\s+[\divxlcdm]+\b.*",            # Chapter 1, Chapter IV
    r"^chapter\s+\w+.*",                        # Chapter One
    r"^#{1,6}\s+\S.*",                          # Markdown headings
    r"^part\s+[\divxlcdm]+\b.*",                # PART 1, PART IV
    r"^part\s+\w+.*",                           # PART ONE
    r"^section\s+[\d]+(?:\.\d+)*\b.*",          # Section 1, Section 1.2
    r"^\d+\.\s+\w+",                            # 1. Introduction
    r"^\d+\s+\w+",                               # 1 Introduction
    r"^[IVX]+\.\s+\w+",                          # I. Overview
    r"^[A-Z][A-Z\s]{3,}$",                         # ALL CAPS HEADINGS
    r"^(introduction|conclusion|abstract|summary)\b.*",
]

_ALL_CAPS_PATTERN = re.compile(r"^[A-Z][A-Z\s]{3,}$")


logger = logging.getLogger(__name__)


class ChapterChunker(BaseChunker):
    """Chunker that splits a document at chapter / section headings.

    The chunker scans each line of the input text and tests it against
    a list of heading patterns.  When a heading is found, all text
    accumulated since the previous heading (or the start of the
    document) is emitted as a chunk, and a new chunk begins with the
    heading line.

    Any text that precedes the first detected heading is emitted as a
    chunk as well (e.g. a preface or title page).

    Args:
        heading_patterns: Optional list of regex pattern strings used
            to detect headings.  Each pattern is matched against a
            stripped line with ``re.IGNORECASE``.  When *None*, a
            sensible set of built-in patterns is used.

    Raises:
        ValueError: If *heading_patterns* is an empty list.
    """

    def __init__(
        self,
        heading_patterns: List[str] | None = None,
        max_chunk_size: Optional[int] = 1024,
        fallback_chunker: Optional[BaseChunker] = None,
        overlap_lines: int = 1,
        length_function: Callable[[str], int] = len,
        debug: bool = False,
    ) -> None:
        if heading_patterns is not None and len(heading_patterns) == 0:
            raise ValueError("heading_patterns must not be an empty list")
        if max_chunk_size is not None and max_chunk_size <= 0:
            raise ValueError("max_chunk_size must be positive when provided")
        if overlap_lines < 0:
            raise ValueError("overlap_lines must be non-negative")

        raw_patterns = heading_patterns or _DEFAULT_HEADING_PATTERNS
        # Pre-compile once for speed.
        self._patterns: List[Pattern[str]] = [
            re.compile(p, re.IGNORECASE) for p in raw_patterns
        ]
        self._raw_patterns = raw_patterns
        self.max_chunk_size = max_chunk_size
        self.fallback_chunker = fallback_chunker
        self.overlap_lines = overlap_lines
        self.length_fn = length_function
        self.debug = debug

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log_debug(self, message: str) -> None:
        if self.debug:
            logger.info("[ChapterChunker] %s", message)

    def _normalize_line(self, line: str) -> str:
        return line.strip()

    def _looks_like_false_positive_all_caps(self, line: str) -> bool:
        stripped = self._normalize_line(line)
        if not _ALL_CAPS_PATTERN.match(stripped):
            return False

        words = stripped.split()
        # Avoid matching short acronyms like "NASA" as headings.
        return len(words) < 2 and len(stripped) < 12

    def _is_heading(self, line: str) -> bool:
        """Return *True* if *line* matches any heading pattern."""
        stripped = self._normalize_line(line)
        if not stripped:
            return False

        if self._looks_like_false_positive_all_caps(stripped):
            return False

        return any(p.match(stripped) for p in self._patterns)

    def _get_heading_level(self, line: str) -> int:
        """Infer a heading level from common heading styles."""
        stripped = self._normalize_line(line)
        lower = stripped.lower()

        if stripped.startswith("#"):
            m = re.match(r"^(#{1,6})\s+", stripped)
            return len(m.group(1)) if m else 3

        if lower.startswith("chapter") or lower.startswith("part"):
            return 1
        if lower.startswith("section"):
            return 2
        if re.match(r"^\d+\.\s+", stripped):
            return 2
        if re.match(r"^\d+\s+", stripped):
            return 2
        if re.match(r"^[IVX]+\.\s+", stripped, re.IGNORECASE):
            return 2
        if re.match(r"^(introduction|conclusion|abstract|summary)\b", lower):
            return 1
        if _ALL_CAPS_PATTERN.match(stripped):
            return 2

        return 2

    def _build_metadata(
        self,
        base_metadata: Dict[str, Any],
        heading: Optional[str],
        heading_level: Optional[int],
        section_index: int,
    ) -> Dict[str, Any]:
        md = base_metadata.copy()
        if heading:
            md["heading"] = heading
        if heading_level is not None:
            md["heading_level"] = heading_level
        md["section_index"] = section_index
        return md

    def _emit_chunk(
        self,
        chunk_text: str,
        start_char: int,
        metadata: Dict[str, Any],
    ) -> Optional[Chunk]:
        if not chunk_text or not chunk_text.strip():
            return None

        return Chunk(
            id=uuid.uuid4(),
            text=chunk_text,
            metadata=metadata,
            start_char=start_char,
            end_char=start_char + len(chunk_text),
        )

    def _split_large_chunk(
        self,
        chunk_text: str,
        start_char: int,
        metadata: Dict[str, Any],
    ) -> List[Chunk]:
        """Split oversized chapter chunks while preserving offsets."""
        if not self.max_chunk_size or self.length_fn(chunk_text) <= self.max_chunk_size:
            single = self._emit_chunk(chunk_text, start_char, metadata.copy())
            return [single] if single else []

        lines: List[str] = chunk_text.splitlines(keepends=True)
        if not lines:
            single = self._emit_chunk(chunk_text, start_char, metadata.copy())
            return [single] if single else []

        chunks: List[Chunk] = []
        i = 0
        rolling_start = start_char

        while i < len(lines):
            current_lines: List[str] = []
            current_len = 0
            j = i

            while j < len(lines):
                line = lines[j]

                if current_lines and (current_len + self.length_fn(line)) > self.max_chunk_size:
                    break

                # Force progress for single very-long lines.
                if not current_lines and self.length_fn(line) > self.max_chunk_size:
                    piece = line[: self.max_chunk_size]
                    chunk = self._emit_chunk(piece, rolling_start, metadata.copy())
                    if chunk:
                        chunks.append(chunk)
                    lines[j] = line[self.max_chunk_size :]
                    rolling_start += len(piece)
                    continue

                current_lines.append(line)
                current_len += self.length_fn(line)
                j += 1

            if current_lines:
                text_part = "".join(current_lines)
                chunk = self._emit_chunk(text_part, rolling_start, metadata.copy())
                if chunk:
                    chunks.append(chunk)

                if self.overlap_lines > 0:
                    overlap = min(self.overlap_lines, len(current_lines))
                    overlap_chars = len("".join(current_lines[-overlap:]))
                    rolling_start += max(1, len(text_part) - overlap_chars)
                    i = max(i + 1, j - overlap)
                else:
                    rolling_start += len(text_part)
                    i = j
            else:
                i += 1

        return chunks

    def _flush_section(
        self,
        chunks: List[Chunk],
        current_lines: List[Tuple[str, int, int]],
        metadata: Dict[str, Any],
        heading: Optional[str],
        heading_level: Optional[int],
        section_index: int,
    ) -> None:
        if not current_lines:
            return

        section_text = "".join(line for line, _, _ in current_lines)
        section_start = current_lines[0][1]
        md = self._build_metadata(metadata, heading, heading_level, section_index)

        produced = self._split_large_chunk(section_text, section_start, md)
        if produced:
            chunks.extend(produced)
            self._log_debug(
                f"Section {section_index} heading={heading!r} start={section_start} size={len(section_text)} produced={len(produced)}"
            )

    def _resolve_fallback_chunker(self) -> BaseChunker:
        if self.fallback_chunker is not None:
            return self.fallback_chunker

        fallback_size = self.max_chunk_size or 800
        fallback_overlap = min(80, max(0, fallback_size // 10))
        return FixedSizeChunker(chunk_size=fallback_size, overlap=fallback_overlap)

    def _apply_fallback(
        self,
        text: str,
        metadata: Dict[str, Any],
    ) -> List[Chunk]:
        fallback = self._resolve_fallback_chunker()
        self._log_debug(
            f"Fallback chunker engaged: {fallback.__class__.__name__}"
        )
        chunks = fallback.chunk(text, metadata)

        # Ensure no empty chunks are returned.
        return [c for c in chunks if c.text and c.text.strip()]

    # ------------------------------------------------------------------
    # BaseChunker interface
    # ------------------------------------------------------------------

    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        """Split *text* into chunks at chapter / section boundaries.

        Each detected chapter or section (including its heading line)
        becomes one chunk.  Text before the first heading is placed in
        its own chunk.  A chunk's character positions refer to the
        original *text*.

        Args:
            text: The full document text.
            metadata: A dictionary of metadata to attach to every
                      generated chunk.

        Returns:
            A list of Chunk objects.  Returns an empty list when
            *text* is empty.
        """
        if not text:
            return []

        lines = text.splitlines(keepends=True)
        chunks: List[Chunk] = []

        current_lines: List[Tuple[str, int, int]] = []
        current_heading: Optional[str] = None
        current_heading_level: Optional[int] = None
        section_index = 0
        char_offset: int = 0
        headings_found = 0

        for line in lines:
            line_start = char_offset
            line_end = line_start + len(line)

            if self._is_heading(line):
                headings_found += 1
                if current_lines:
                    self._flush_section(
                        chunks=chunks,
                        current_lines=current_lines,
                        metadata=metadata,
                        heading=current_heading,
                        heading_level=current_heading_level,
                        section_index=section_index,
                    )
                    section_index += 1
                    current_lines = []

                current_heading = self._normalize_line(line)
                current_heading_level = self._get_heading_level(line)
                self._log_debug(
                    f"Detected heading: {current_heading!r} level={current_heading_level} at {line_start}"
                )

            current_lines.append((line, line_start, line_end))
            char_offset += len(line)

        # Flush any remaining text.
        if current_lines:
            self._flush_section(
                chunks=chunks,
                current_lines=current_lines,
                metadata=metadata,
                heading=current_heading,
                heading_level=current_heading_level,
                section_index=section_index,
            )

        chunks = [c for c in chunks if c.text and c.text.strip()]

        # Fallback only when heading detection found nothing at all.
        # Producing a single chapter-sized chunk is a valid outcome and
        # should not trigger a re-chunk via fixed-size splitting.
        if headings_found == 0:
            # Only engage the fallback chunker if the text is genuinely too
            # large to be returned as one chunk.  Short heading-free documents
            # are emitted as a single chunk without any re-chunking.
            if self.max_chunk_size and self.length_fn(text) > self.max_chunk_size:
                return self._apply_fallback(text=text, metadata=metadata)
            # Short document: emit as one chunk.
            single = self._emit_chunk(
                text,
                0,
                self._build_metadata(metadata, None, None, 0),
            )
            return [single] if single else []

        return chunks

    def get_config(self) -> Dict[str, Any]:
        """Return the chunker's current configuration.

        Returns:
            A dict with the strategy name and the heading patterns
            in use.
        """
        return {
            "strategy": "chapter_based",
            "heading_patterns": self._raw_patterns,
            "max_chunk_size": self.max_chunk_size,
            "overlap_lines": self.overlap_lines,
            "length_function": getattr(self.length_fn, "__name__", repr(self.length_fn)),
            "fallback_chunker": (
                self.fallback_chunker.__class__.__name__
                if self.fallback_chunker is not None
                else "fixed_size"
            ),
            "debug": self.debug,
        }
