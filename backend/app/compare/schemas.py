from typing import List

from pydantic import BaseModel, Field, model_validator

from app.compare.utils import derive_collection_name


class RAGConfig(BaseModel):
    name: str
    chunk_strategy: str = Field(..., pattern="^(fixed|semantic|recursive)$")
    embedding_model: str = Field(..., pattern="^(nvidia|huggingface)$")
    top_k: int = Field(..., ge=1, le=10)
    threshold: float = Field(..., ge=0.0, le=1.0)
    collection_name: str = ""

    @model_validator(mode="after")
    def _populate_collection_name(self):
        self.collection_name = derive_collection_name(self.embedding_model, self.chunk_strategy)
        return self


class IndexRequest(BaseModel):
    config: RAGConfig


class IndexResponse(BaseModel):
    config_name: str
    collection_name: str
    chunk_count: int
    status: str


class ConfigResult(BaseModel):
    config: RAGConfig
    answer: str
    chunks: List[str]
    scores: List[float]
    latency_ms: float
    avg_similarity: float
    chunk_count: int


class CompareRequest(BaseModel):
    query: str
    configs: List[RAGConfig] = Field(..., min_length=1, max_length=4)


class CompareResponse(BaseModel):
    query: str
    results: List[ConfigResult]
