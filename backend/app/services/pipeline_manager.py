"""Pipeline manager.

This module preserves the historical entrypoint used by the API, but it no
longer caches user-specific pipelines. A fresh pipeline is created for each
request so request state cannot leak between users or workers.
"""

from typing import Any, Dict

from app.services.pipeline_factory import PipelineFactory
from app.services.rag_pipeline import RAGPipeline


class PipelineManager:
    """Create fresh pipelines on demand."""

    @classmethod
    def get_pipeline(cls, config_id: str, config_json: Dict[str, Any]) -> RAGPipeline:
        _ = config_id  # retained for call-site compatibility and logging hooks.
        return PipelineFactory.create_pipeline(config_json)

    @classmethod
    def clear_cache(cls):
        """No-op retained for compatibility."""
        return None
