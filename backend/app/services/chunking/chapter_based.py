"""
Chapter-based chunking strategy.

Splits text at detected chapter or section headings so that each
chapter / section becomes its own chunk.
"""

import re
import uuid
from typing import Any, Dict, List, Pattern

from backend.app.services.chunking.base import BaseChunker, Chunk

# Default heading patterns (case-insensitive, matched at line start):
#   • "Chapter 1", "Chapter IV", "Chapter One" …
#   • Markdown headings: "# …", "## …", "### …"
#   • "PART ONE", "PART 1", "PART IV" …
#   • "Section 1", "Section 1.2" …
#   • A line written entirely in UPPER-CASE (≥4 chars, common in
#     plain-text books for chapter titles)
_DEFAULT_HEADING_PATTERNS: List[str] = [
    r"^chapter\s+[\divxlcdm]+\b.*",       # Chapter 1, Chapter IV …
    r"^chapter\s+\w+.*",                   # Chapter One …
    r"^#{1,6}\s+\S.*",                     # Markdown headings
    r"^part\s+[\divxlcdm]+\b.*",           # PART 1, PART IV …
    r"^part\s+\w+.*",                      # PART ONE …
    r"^section\s+[\d]+(?:\.\d+)*\b.*",     # Section 1, Section 1.2 …
]


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
    ) -> None:
        if heading_patterns is not None and len(heading_patterns) == 0:
            raise ValueError("heading_patterns must not be an empty list")

        raw_patterns = heading_patterns or _DEFAULT_HEADING_PATTERNS
        # Pre-compile once for speed.
        self._patterns: List[Pattern[str]] = [
            re.compile(p, re.IGNORECASE) for p in raw_patterns
        ]
        self._raw_patterns = raw_patterns

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_heading(self, line: str) -> bool:
        """Return *True* if *line* matches any heading pattern."""
        stripped = line.strip()
        return any(p.match(stripped) for p in self._patterns)

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

        current_lines: List[str] = []
        current_start: int = 0  # character offset of the current chunk
        char_offset: int = 0    # running character offset

        for line in lines:
            if self._is_heading(line) and current_lines:
                # Flush accumulated lines as a chunk.
                chunk_text = "".join(current_lines)
                chunks.append(
                    Chunk(
                        id=uuid.uuid4(),
                        text=chunk_text,
                        metadata=metadata.copy(),
                        start_char=current_start,
                        end_char=current_start + len(chunk_text),
                    )
                )
                current_lines = []
                current_start = char_offset

            current_lines.append(line)
            char_offset += len(line)

        # Flush any remaining text.
        if current_lines:
            chunk_text = "".join(current_lines)
            chunks.append(
                Chunk(
                    id=uuid.uuid4(),
                    text=chunk_text,
                    metadata=metadata.copy(),
                    start_char=current_start,
                    end_char=current_start + len(chunk_text),
                )
            )

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
        }
