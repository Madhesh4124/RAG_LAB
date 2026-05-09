"""Text cleanup helpers for extracted document text."""

from __future__ import annotations

import re


_BULLETISH_CHARS = {
    "\x7f": "\n- ",
    "\u2022": "\n- ",
    "\u25aa": "\n- ",
    "\u25cf": "\n- ",
    "\uf0b7": "\n- ",
}


def normalize_extracted_text(text: str) -> str:
    """Normalize common PDF extraction artifacts before chunking.

    Some PDFs extract bullets as control characters such as DEL (shown in the
    UI as ````). Treating these as separators gives chunkers cleaner semantic
    boundaries and prevents unrelated bullet points from being glued together.
    """
    value = str(text or "")
    for raw, replacement in _BULLETISH_CHARS.items():
        value = value.replace(raw, replacement)

    # Drop remaining non-whitespace control characters, but preserve newlines.
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()
