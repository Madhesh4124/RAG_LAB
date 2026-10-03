from copy import deepcopy
from typing import Any, Dict

BEST_PRESET_VERSION = "v5"
BEST_PRESET_NAME = "Best Preset"

_BEST_PRESET_CONFIG: Dict[str, Any] = {
    "chunker": {"type": "sentence_window", "window_size": 5, "max_chunk_size": 150},
    "embedder": {"provider": "nvidia", "model": "nvidia/nemotron-3-embed-1b"},
    "vectorstore": {"type": "chroma"},
    "retriever": {
        "type": "hybrid",
        "retrieval_type": "hybrid",
        "top_k": 4,
        "rerank_fetch_k": 5,
        "similarity_threshold": 0.35,
        "alpha": 0.7,
        "lambda_mult": 0.5,
        "reranker_enabled": True,
        "reranker_provider": "huggingface_api",
        "reranker_model": "BAAI/bge-reranker-v2-m3",
        "min_candidates": 3,
    },
    "llm": {"provider": "gemini", "model": "gemini-2.5-flash"},
    "memory": {"type": "buffer", "max_turns": 6, "max_turns_before_summary": 4},
}


def get_best_preset_config() -> Dict[str, Any]:
    return deepcopy(_BEST_PRESET_CONFIG)
