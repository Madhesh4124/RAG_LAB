"""Rate limiting middleware and utilities for API calls."""

import os
import time
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple
from uuid import UUID

logger = logging.getLogger(__name__)


class APIRateLimiter:
    """
    Track and enforce rate limits per user.
    
    - LLM calls: max 5 per hour
    - Default: cooldown per call type to prevent burst
    """

    def __init__(self):
        self.max_llm_calls_per_hour = int(os.getenv("MAX_LLM_CALLS_PER_HOUR", "15"))
        self.max_embedding_calls_per_hour = int(os.getenv("MAX_EMBEDDING_CALLS_PER_HOUR", "50"))
        self.max_retrieval_calls_per_hour = int(os.getenv("MAX_RETRIEVAL_CALLS_PER_HOUR", "100"))
        
        # In-memory store: {user_id: {call_type: [(timestamp, ...], ...}}}
        self._call_history: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))

    def check_rate_limit(self, user_id: UUID, call_type: str = "llm") -> Tuple[bool, int, str]:
        """
        Check if user has exceeded rate limit for the call type.
        
        Returns:
            (allowed: bool, remaining: int, error_message: str)
        """
        user_key = str(user_id)
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)

        # Clean old calls outside 1-hour window
        if user_key in self._call_history:
            for ctype in self._call_history[user_key]:
                self._call_history[user_key][ctype] = [
                    ts for ts in self._call_history[user_key][ctype]
                    if ts > one_hour_ago
                ]

        # Get limit for call type
        limits = {
            "llm": self.max_llm_calls_per_hour,
            "embedding": self.max_embedding_calls_per_hour,
            "retrieval": self.max_retrieval_calls_per_hour,
        }
        limit = limits.get(call_type, limits["llm"])

        # Count calls in past hour
        call_count = len(self._call_history[user_key][call_type])
        remaining = max(0, limit - call_count)

        if call_count >= limit:
            return False, remaining, f"Rate limit exceeded: {call_count}/{limit} {call_type} calls in the past hour"

        return True, remaining, ""

    def record_call(self, user_id: UUID, call_type: str = "llm") -> None:
        """Record a successful API call."""
        user_key = str(user_id)
        now = datetime.now(timezone.utc)
        self._call_history[user_key][call_type].append(now)

    def record_rate_limit_error(self, user_id: UUID, call_type: str = "llm", error_message: str = "") -> dict:
        """Record a rate limit error event for monitoring."""
        return {
            "user_id": str(user_id),
            "call_type": call_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": error_message,
        }


# Global rate limiter instance
_rate_limiter = APIRateLimiter()


def get_rate_limiter() -> APIRateLimiter:
    """Get the global rate limiter instance."""
    return _rate_limiter
