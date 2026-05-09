"""Pipeline manager.

Production-hardened pipeline cache with:
- TTL-based expiry (PIPELINE_CACHE_TTL_SECONDS, default 3600 s).
- Per-(user, config) asyncio.Lock to prevent concurrent double-indexing (P1.3).
- Config-content-hash keying so JSON field-order variations don't create duplicate
  cache entries (P2.4).
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from app.services.pipeline_factory import PipelineFactory
from app.services.rag_pipeline import RAGPipeline

logger = logging.getLogger(__name__)

_PIPELINE_CACHE_TTL: int = int(os.getenv("PIPELINE_CACHE_TTL_SECONDS", "3600"))


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
    _cache_lock: asyncio.Lock = asyncio.Lock()

    # Per-key indexing locks — prevent concurrent double-indexing for same doc/config.
    _indexing_locks: Dict[str, asyncio.Lock] = {}
    _lock_registry_lock: asyncio.Lock = asyncio.Lock()

    @classmethod
    def _config_hash(cls, config_json: Dict[str, Any]) -> str:
        """Stable SHA-256 hash of a config dict, independent of key ordering."""
        serialized = json.dumps(config_json, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    @classmethod
    def get_pipeline(cls, cache_key: str, config_json: Dict[str, Any]) -> RAGPipeline:
        """Returns a live (non-expired) cached pipeline or creates a new one.

        Args:
            cache_key: Opaque string, typically ``"{user_id}:{config_id}"``.
            config_json: Full pipeline configuration dict.
        """
        config_hash = cls._config_hash(config_json)
        entry = cls._cache.get(cache_key)

        if entry is not None and not entry.is_expired() and entry.config_hash == config_hash:
            return entry.pipeline

        # Cache miss, expiry, or config change — build a new pipeline.
        logger.debug("PipelineManager: creating pipeline for key=%s", cache_key)
        pipeline = PipelineFactory.create_pipeline(config_json)
        cls._cache[cache_key] = _CacheEntry(pipeline=pipeline, config_hash=config_hash)
        return pipeline

    @classmethod
    async def get_indexing_lock(cls, key: str) -> asyncio.Lock:
        """Return a per-key asyncio.Lock for serialising indexing of the same document.

        Callers should use ``async with await PipelineManager.get_indexing_lock(key):``.
        """
        async with cls._lock_registry_lock:
            if key not in cls._indexing_locks:
                cls._indexing_locks[key] = asyncio.Lock()
            return cls._indexing_locks[key]

    @classmethod
    def invalidate(cls, cache_key: str) -> None:
        """Explicitly evict a single pipeline from the cache."""
        cls._cache.pop(cache_key, None)
        logger.info("PipelineManager: evicted pipeline cache for key=%s", cache_key)

    @classmethod
    def clear_cache(cls) -> None:
        """Clears the entire pipeline cache."""
        cls._cache.clear()
        logger.info("PipelineManager: full cache cleared")
