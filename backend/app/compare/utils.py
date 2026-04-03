from typing import List, Tuple


def derive_collection_name(embedding_model: str, chunk_strategy: str) -> str:
    # Include concrete model identity in collection names so previously indexed
    # collections with different embedding dimensions do not collide.
    model_key = {
        "nvidia": "nv_embed_v1",
        "huggingface": "all_minilm_l6_v2",
    }.get(embedding_model, embedding_model)
    return f"{embedding_model}_{model_key}_{chunk_strategy}".lower().replace(" ", "_")


def calc_avg_similarity(scores: List[float]) -> float:
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 4)


def filter_by_threshold(chunks_and_scores: List[Tuple], threshold: float) -> List[Tuple]:
    return [item for item in chunks_and_scores if float(item[1]) >= threshold]
