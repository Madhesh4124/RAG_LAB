import hashlib
import json
from typing import Any, List, Tuple


def derive_config_signature(config: Any, user_scope: str | None = None) -> str:
    payload = {
        "user_scope": user_scope or "",
        "embedding_provider": getattr(config, "embedding_provider", None),
        "embedding_model": getattr(config, "embedding_model", None),
        "chunk_strategy": getattr(config, "chunk_strategy", None),
        "chunk_params": getattr(config, "chunk_params", {}) or {},
        "top_k": getattr(config, "top_k", None),
        "threshold": getattr(config, "threshold", None),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def derive_collection_name(embedding_provider: str, embedding_model: str, chunk_strategy: str) -> str:
    # Include provider + concrete model identity in collection names so
    # collections using different embedding dimensions never collide.
    normalized_model = (
        embedding_model.lower()
        .replace("/", "_")
        .replace("-", "_")
        .replace(" ", "_")
        .replace(".", "_")
    )
    return f"{embedding_provider}_{normalized_model}_{chunk_strategy}".lower()


def calc_avg_similarity(scores: List[float]) -> float:
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 4)


def filter_by_threshold(chunks_and_scores: List[Tuple], threshold: float) -> List[Tuple]:
    return [item for item in chunks_and_scores if float(item[1]) >= threshold]
