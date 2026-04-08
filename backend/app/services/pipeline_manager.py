"""Pipeline manager.

This module preserves the historical entrypoint used by the API, but it now
caches user-specific pipelines using an LRU cache to avoid re-initializing
heavy resources like embedding models and LLM clients on every request.
"""

from functools import lru_cache
from typing import Any, Dict

from app.services.pipeline_factory import PipelineFactory
from app.services.rag_pipeline import RAGPipeline


class PipelineManager:
    """Create and cache pipelines on demand."""

    @classmethod
    def get_pipeline(cls, config_id: str, config_json: Dict[str, Any]) -> RAGPipeline:
        """Returns a cached pipeline or creates a new one if not found."""
        import json
        return cls._get_cached_pipeline(config_id, json.dumps(config_json, sort_keys=True))

    @staticmethod
    @lru_cache(maxsize=32)
    def _get_cached_pipeline(config_id: str, config_str: str) -> RAGPipeline:
        import json
        config_json = json.loads(config_str)
        return PipelineFactory.create_pipeline(config_json)

    @classmethod
    def clear_cache(cls):
        """Clears the pipeline cache."""
        cls._get_cached_pipeline.cache_clear()
        return None
