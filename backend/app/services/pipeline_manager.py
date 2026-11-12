"""Pipeline manager.

Production-hardened pipeline cache with:
- TTL-based expiry (PIPELINE_CACHE_TTL_SECONDS, default 3600 s).
- Per-(user, config) asyncio.Lock with bounded lock registry & loop awareness (P1.3).
- Config-content-hash keying so JSON field-order variations don't create duplicate
  cache entries (P2.4).
"""

import asyncio
import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict

from app.services.pipeline_factory import PipelineFactory
from app.services.rag_pipeline import RAGPipeline

logger = logging.getLogger(__name__)

_PIPELINE_CACHE_TTL: int = int(os.getenv("PIPELINE_CACHE_TTL_SECONDS", "3600"))
_MAX_INDEXING_LOCKS: int = max(1, int(os.getenv("PIPELINE_LOCK_MAX_ENTRIES", "512")))


@dataclass
class _CacheEntry:
    pipeline: RAGPipeline
    created_at: float = field(default_factory=time.monotonic)
    config_hash: str = ""

    def is_expired(self, ttl: int = _PIPELINE_CACHE_TTL) -> bool:
        return (time.monotonic() - self.created_at) > ttl


class PipelineManager:
    """Create and cache pipelines on demand."""

    # Pipeline cache: key = "{user_id}:{config_id}"
    _cache: Dict[str, _CacheEntry] = {}
    _cache_lock: threading.RLock = threading.RLock()

    # Per-key indexing locks — prevent concurrent double-indexing for same doc/config.
    _indexing_locks: Dict[str, asyncio.Lock] = {}
    _lock_registry_lock: threading.RLock = threading.RLock()

    @classmethod
    def _config_hash(cls, config_json: Dict[str, Any]) -> str:
        """Stable SHA-256 hash of a config dict, independent of key ordering."""
        serialized = json.dumps(config_json, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    @classmethod
    def get_pipeline(cls, cache_key: str, config_json: Dict[str, Any]) -> RAGPipeline:
        """Returns a live (non-expired) cached pipeline or creates a new one."""
        config_hash = cls._config_hash(config_json)
        with cls._cache_lock:
            # Lazily prune expired cache entries while reading.
            for k in [k for k, v in cls._cache.items() if v.is_expired()]:
                cls._cache.pop(k, None)

            entry = cls._cache.get(cache_key)
            if entry is not None and not entry.is_expired() and entry.config_hash == config_hash:
                return entry.pipeline

        # Build outside the registry lock to keep lock hold minimal, then store safely.
        logger.debug("PipelineManager: creating pipeline for key=%s", cache_key)
        pipeline = PipelineFactory.create_pipeline(config_json)
        with cls._cache_lock:
            cls._cache[cache_key] = _CacheEntry(pipeline=pipeline, config_hash=config_hash)
        return pipeline

    @classmethod
    def _prune_unlocked_locks_locked(cls, max_entries: int | None = None) -> None:
        limit = _MAX_INDEXING_LOCKS if max_entries is None else max(1, int(max_entries))
        if len(cls._indexing_locks) < limit:
            return
        for candidate_key in list(cls._indexing_locks.keys()):
            if len(cls._indexing_locks) < limit:
                break
            lock = cls._indexing_locks.get(candidate_key)
            if lock is not None and not lock.locked():
                cls._indexing_locks.pop(candidate_key, None)

    @classmethod
    async def get_indexing_lock(cls, key: str) -> asyncio.Lock:
        """Return a per-key asyncio.Lock for serialising indexing of the same document.

        Callers should use ``async with await PipelineManager.get_indexing_lock(key):``.
        """
        with cls._lock_registry_lock:
            existing = cls._indexing_locks.get(key)
            if existing is not None:
                return existing
            cls._prune_unlocked_locks_locked()
            lock = asyncio.Lock()
            cls._indexing_locks[key] = lock
            return lock

    @classmethod
    def invalidate(cls, cache_key: str) -> None:
        """Explicitly evict a single pipeline from the cache and prune its unlocked lock."""
        with cls._cache_lock:
            cls._cache.pop(cache_key, None)
        with cls._lock_registry_lock:
            lock = cls._indexing_locks.get(cache_key)
            if lock is not None and not lock.locked():
                cls._indexing_locks.pop(cache_key, None)
        logger.info("PipelineManager: evicted pipeline cache for key=%s", cache_key)

    @classmethod
    def clear_cache(cls) -> None:
        """Clears the entire pipeline cache and prunes unlocked indexing locks."""
        with cls._cache_lock:
            cls._cache.clear()
        with cls._lock_registry_lock:
            for key in [k for k, lock in cls._indexing_locks.items() if not lock.locked()]:
                cls._indexing_locks.pop(key, None)
        logger.info("PipelineManager: full cache cleared")
