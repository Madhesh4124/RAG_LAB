"""
Pipeline Manager.

Maintains an in-memory cache of initialized RAGPipeline instances to prevent 
redundant indexing (especially for non-persisted retrievers like BM25).
"""

import logging
from typing import Dict, Optional, Any
from app.services.rag_pipeline import RAGPipeline
from app.services.pipeline_factory import PipelineFactory

logger = logging.getLogger(__name__)

class PipelineManager:
    """Manages active RAGPipeline instances with simple in-memory caching."""
    
    _cache: Dict[str, RAGPipeline] = {}
    
    @classmethod
    def get_pipeline(cls, config_id: str, config_json: Dict[str, Any]) -> RAGPipeline:
        """Fetch a cached pipeline or create a new one."""
        if config_id in cls._cache:
            logger.info(f"Retrieved pipeline from cache for config_id: {config_id}")
            return cls._cache[config_id]
            
        logger.info(f"Creating new pipeline instance for config_id: {config_id}")
        pipeline = PipelineFactory.create_pipeline(config_json)
        cls._cache[config_id] = pipeline
        
        # Limit cache size (primitive eviction)
        if len(cls._cache) > 10:
            oldest_key = next(iter(cls._cache))
            del cls._cache[oldest_key]
            
        return pipeline

    @classmethod
    def clear_cache(cls):
        cls._cache.clear()
