"""Indexing job store for async background indexing (P2.1).

Tracks the status of background document-indexing tasks with an explicit
state machine (``pending -> indexing -> ready | failed``) so that ``/prepare``
can return immediately with a ``job_id`` and the frontend can poll
``GET /api/documents/index-status/{job_id}`` for progress.

This implementation stores job state in-memory.  For multi-process / multi-node
deployments, replace ``_jobs`` with a Redis hash or a DB table.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)


class IndexingState(str, Enum):
    PENDING = "pending"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


TERMINAL_STATES: Set[IndexingState] = {IndexingState.READY, IndexingState.FAILED}

ALLOWED_TRANSITIONS: Dict[IndexingState, Set[IndexingState]] = {
    IndexingState.PENDING: {IndexingState.INDEXING, IndexingState.READY, IndexingState.FAILED},
    IndexingState.INDEXING: {IndexingState.INDEXING, IndexingState.READY, IndexingState.FAILED},
    IndexingState.READY: set(),
    IndexingState.FAILED: set(),
}


@dataclass
class IndexingJob:
    job_id: str
    doc_id: str
    config_id: str
    user_id: Optional[str] = None
    doc_key: Optional[str] = None
    status: str = IndexingState.PENDING.value
    progress_pct: int = 0            # 0-100
    error: Optional[str] = None
    created_at: float = field(default_factory=time.monotonic)
    updated_at: float = field(default_factory=time.monotonic)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "doc_id": self.doc_id,
            "config_id": self.config_id,
            "status": self.status,
            "progress_pct": self.progress_pct,
            "error": self.error,
        }


class IndexingJobStore:
    """Thread-safe in-memory store for indexing job state."""

    _jobs: Dict[str, IndexingJob] = {}
    _lock: threading.RLock = threading.RLock()
    # Evict completed/failed jobs older than 2 hours; keep active jobs much longer.
    _TTL_SECONDS: int = 7200
    _STALE_ACTIVE_TTL_SECONDS: int = 21600

    @classmethod
    def create(
        cls,
        doc_id: str,
        config_id: str,
        user_id: Optional[str] = None,
        doc_key: Optional[str] = None,
    ) -> str:
        """Create a new job and return its ``job_id``."""
        with cls._lock:
            job_id = str(uuid.uuid4())
            cls._jobs[job_id] = IndexingJob(
                job_id=job_id,
                doc_id=str(doc_id),
                config_id=str(config_id),
                user_id=str(user_id) if user_id is not None else None,
                doc_key=doc_key,
            )
            cls._evict_expired()
            return job_id

    @classmethod
    def find_active_job(
        cls,
        *,
        user_id: str,
        config_id: str,
        doc_key: Optional[str] = None,
    ) -> Optional[IndexingJob]:
        """Return an in-flight (pending/indexing) job matching the same scope."""
        with cls._lock:
            for job in cls._jobs.values():
                if job.status not in (IndexingState.PENDING.value, IndexingState.INDEXING.value):
                    continue
                if job.user_id != str(user_id) or job.config_id != str(config_id):
                    continue
                if doc_key is not None and job.doc_key != doc_key:
                    continue
                return job
            return None

    @classmethod
    def update(
        cls,
        job_id: str,
        *,
        status: Optional[str] = None,
        progress_pct: Optional[int] = None,
        error: Optional[str] = None,
    ) -> bool:
        """Update job fields in place, enforcing valid state transitions."""
        with cls._lock:
            job = cls._jobs.get(job_id)
            if job is None:
                return False

            current_state = IndexingState(job.status)
            if status is not None:
                next_state = IndexingState(status)
                if next_state != current_state and next_state not in ALLOWED_TRANSITIONS[current_state]:
                    logger.warning(
                        "Ignoring invalid IndexingJob transition %s -> %s for job_id=%s",
                        current_state.value,
                        next_state.value,
                        job_id,
                    )
                    return False
                job.status = next_state.value
                current_state = next_state

            if progress_pct is not None:
                if current_state not in TERMINAL_STATES or current_state == IndexingState.READY:
                    job.progress_pct = min(100, max(0, progress_pct))

            if error is not None:
                job.error = error

            job.updated_at = time.monotonic()
            return True

    @classmethod
    def get(cls, job_id: str) -> Optional[IndexingJob]:
        with cls._lock:
            return cls._jobs.get(job_id)

    @classmethod
    def _evict_expired(cls) -> None:
        now = time.monotonic()
        terminal_cutoff = now - cls._TTL_SECONDS
        active_cutoff = now - cls._STALE_ACTIVE_TTL_SECONDS
        expired = []
        for jid, job in cls._jobs.items():
            is_terminal = job.status in (IndexingState.READY.value, IndexingState.FAILED.value)
            if is_terminal and job.updated_at < terminal_cutoff:
                expired.append(jid)
            elif not is_terminal and job.created_at < active_cutoff:
                expired.append(jid)
        for jid in expired:
            del cls._jobs[jid]
