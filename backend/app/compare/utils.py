from typing import List, Tuple


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
