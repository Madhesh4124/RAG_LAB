from copy import deepcopy
from typing import Any, Dict

BEST_PRESET_VERSION = "v1"
BEST_PRESET_NAME = "Best Preset"

_BEST_PRESET_CONFIG: Dict[str, Any] = {
    "chunker": {"type": "semantic", "max_chunk_size": 512, "min_chunk_size": 100, "similarity_threshold": 0.7, "hard_split_threshold": 0.4, "overlap_sentences": 1},
    "embedder": {"provider": "nvidia", "model": "nvidia/nv-embed-v1"},
    "vectorstore": {"type": "chroma"},
    "retriever": {
        "type": "hybrid",
        "retrieval_type": "hybrid",
        "top_k": 5,
        "similarity_threshold": 0.0,
        "alpha": 0.7,
        "lambda_mult": 0.5,
        "reranker_enabled": True,
        "reranker_provider": "huggingface_api",
        "reranker_model": "BAAI/bge-reranker-base",
    },
    "llm": {"provider": "gemini", "model": "gemma-4-26b-a4b-it"},
    "memory": {"type": "buffer", "max_turns": 5, "max_turns_before_summary": 5},
}


def get_best_preset_config() -> Dict[str, Any]:
    return deepcopy(_BEST_PRESET_CONFIG)
