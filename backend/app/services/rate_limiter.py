"""Database-backed rate limiting utilities for API calls."""

import os
from datetime import datetime, timedelta, timezone
from typing import Tuple
from uuid import UUID

from fastapi import Depends
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.rate_limit import RateLimitEvent


class RateLimitExceededException(Exception):
    """Raised when a request exceeds configured rate limits."""

    def __init__(self, scope_key: str, call_type: str, message: str):
        super().__init__(message)
        self.scope_key = scope_key
        self.call_type = call_type
        self.message = message


class DatabaseRateLimiter:
    """Track and enforce rate limits using shared database state.

    This is safe across multiple workers because counters are derived from
    persisted rows instead of process memory.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.max_llm_calls_per_hour = int(os.getenv("MAX_LLM_CALLS_PER_HOUR", "15"))
        self.max_embedding_calls_per_hour = int(os.getenv("MAX_EMBEDDING_CALLS_PER_HOUR", "50"))
        self.max_retrieval_calls_per_hour = int(os.getenv("MAX_RETRIEVAL_CALLS_PER_HOUR", "100"))

    @staticmethod
    def build_scope_key(user_id: UUID | None = None, ip_address: str | None = None) -> str:
        if user_id is not None:
            return f"user:{user_id}"
        if ip_address:
            return f"ip:{ip_address}"
        return "anonymous"

    def _limit_for(self, call_type: str) -> int:
        limits = {
            "llm": self.max_llm_calls_per_hour,
            "embedding": self.max_embedding_calls_per_hour,
            "retrieval": self.max_retrieval_calls_per_hour,
        }
        return limits.get(call_type, limits["llm"])

    async def _prune_old_events(self, scope_key: str, call_type: str) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        await self.db.execute(
            delete(RateLimitEvent).where(
                RateLimitEvent.scope_key == scope_key,
                RateLimitEvent.call_type == call_type,
                RateLimitEvent.created_at < cutoff,
            )
        )
        await self.db.commit()

    async def check_rate_limit(self, scope_key: str, call_type: str = "llm") -> Tuple[bool, int, str]:
        """Return whether the request is allowed and how many calls remain."""
        await self._prune_old_events(scope_key, call_type)

        limit = self._limit_for(call_type)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

        result = await self.db.execute(
            select(func.count())
            .select_from(RateLimitEvent)
            .where(
                RateLimitEvent.scope_key == scope_key,
                RateLimitEvent.call_type == call_type,
                RateLimitEvent.created_at >= cutoff,
            )
        )
        call_count = int(result.scalar_one())
        remaining = max(0, limit - call_count)

        if call_count >= limit:
            return False, remaining, f"Rate limit exceeded: {call_count}/{limit} {call_type} calls in the past hour"

        return True, remaining, ""

    async def record_call(self, scope_key: str, call_type: str = "llm", user_id: UUID | None = None) -> None:
        """Record a successful API call in persistent storage."""
        self.db.add(
            RateLimitEvent(
                user_id=user_id,
                scope_key=scope_key,
                call_type=call_type,
            )
        )
        await self.db.commit()

    @staticmethod
    def record_rate_limit_error(scope_key: str, call_type: str = "llm", error_message: str = "") -> dict:
        """Return a structured error event for monitoring and logging."""
        return {
            "scope_key": scope_key,
            "call_type": call_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": error_message,
        }

    async def enforce_rate_limit(self, scope_key: str, call_type: str = "llm") -> None:
        """Raise a typed exception when the current scope is over limit."""
        allowed, _, error_msg = await self.check_rate_limit(scope_key, call_type)
        if not allowed:
            raise RateLimitExceededException(
                scope_key=scope_key,
                call_type=call_type,
                message=error_msg,
            )


async def get_rate_limiter(db: AsyncSession = Depends(get_db)) -> DatabaseRateLimiter:
    """Dependency that creates a request-scoped rate limiter."""
    return DatabaseRateLimiter(db)
