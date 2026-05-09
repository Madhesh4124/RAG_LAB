"""Indexing job store for async background indexing (P2.1).

Tracks the status of background document-indexing tasks so that ``/prepare``
can return immediately with a ``job_id`` and the frontend can poll
``GET /api/documents/{job_id}/index-status`` for progress.

This implementation stores job state in-memory.  For multi-process / multi-node
deployments, replace ``_jobs`` with a Redis hash or a DB table.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class IndexingJob:
    job_id: str
    doc_id: str
    config_id: str
    status: str = "pending"          # pending | indexing | ready | failed
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
    # Simple TTL: evict jobs older than 2 hours to prevent unbounded growth.
    _TTL_SECONDS: int = 7200

    @classmethod
    def create(cls, doc_id: str, config_id: str) -> str:
        """Create a new job and return its ``job_id``."""
        job_id = str(uuid.uuid4())
        cls._jobs[job_id] = IndexingJob(job_id=job_id, doc_id=str(doc_id), config_id=str(config_id))
        cls._evict_expired()
        return job_id

    @classmethod
    def update(
        cls,
        job_id: str,
        *,
        status: Optional[str] = None,
        progress_pct: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update job fields in place."""
        job = cls._jobs.get(job_id)
        if job is None:
            return
        if status is not None:
            job.status = status
        if progress_pct is not None:
            job.progress_pct = min(100, max(0, progress_pct))
        if error is not None:
            job.error = error
        job.updated_at = time.monotonic()

    @classmethod
    def get(cls, job_id: str) -> Optional[IndexingJob]:
        return cls._jobs.get(job_id)

    @classmethod
    def _evict_expired(cls) -> None:
        cutoff = time.monotonic() - cls._TTL_SECONDS
        expired = [jid for jid, job in cls._jobs.items() if job.created_at < cutoff]
        for jid in expired:
            del cls._jobs[jid]
