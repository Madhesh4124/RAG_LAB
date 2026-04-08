import re
from typing import Literal

# Explicit whole-document intents only.
GLOBAL_QUERY_PATTERNS = (
    r"\bsummary\b",
    r"\bsummarize\b",
    r"\boverview\b",
    r"\bmain idea\b",
    r"\bkey points?\b",
    r"\bkey takeaways?\b",
    r"\b(?:what|which)\s+(?:is\s+)?(?:the\s+)?(?:model|system)\s+(?:being\s+)?(?:trained|fine[-\s]?tuned)\s+(?:for|to\s+do)\b",
    r"\bfor\s+what\s+(?:is\s+)?(?:the\s+)?(?:model|system)\s+(?:being\s+)?(?:trained|fine[-\s]?tuned)\b",
    r"\b(?:purpose|objective|goal)\s+of\s+(?:the\s+)?(?:model|training|study)\b",
    r"\b(?:what is|what's) (?:this|the) (?:document|file|text) (?:about|on)\b",
    r"\b(?:about|summary of) (?:this|the) (?:document|file|text)\b",
)

# Specific-target intents should use retrieval mode.
LOCAL_OVERRIDE_PATTERNS = (
    r"\bphase\s*\d+\b",
    r"\b(first|second|third|fourth) phase\b",
    r"\b(section|chapter|page)\b",
    r"\b(explain|describe|details?)\b",
)


def classify_query(query: str) -> Literal["global", "local"]:
    q = (query or "").strip().lower()
    if not q:
        return "local"

    if any(re.search(pattern, q) for pattern in LOCAL_OVERRIDE_PATTERNS):
        return "local"

    if any(re.search(pattern, q) for pattern in GLOBAL_QUERY_PATTERNS):
        return "global"

    return "local"
