import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from app.compare.utils import derive_collection_name


class RAGConfig(BaseModel):
    name: str
    chunk_strategy: str = Field(
        ...,
        pattern="^(fixed|fixed_size|semantic|recursive|chapter|chapter_based|regex|sentence_window)$",
    )
    embedding_provider: Optional[str] = Field(default=None, pattern="^(nvidia|huggingface|google)$")
    embedding_model: str
    chunk_params: Dict[str, Any] = Field(default_factory=dict)
    top_k: int = Field(..., ge=1, le=10)
    threshold: float = Field(..., ge=0.0, le=1.0)
    collection_name: str = ""
    reranker_enabled: bool = False
    reranker_model: Optional[str] = "BAAI/bge-reranker-v2-m3"
    reranker_provider: Optional[str] = "huggingface_api"

    @model_validator(mode="after")
    def _populate_collection_name(self):
        strategy_alias = {
            "fixed": "fixed_size",
            "chapter": "chapter_based",
        }
        self.chunk_strategy = strategy_alias.get(self.chunk_strategy, self.chunk_strategy)

        default_model_by_provider = {
            "nvidia": "nvidia/nemotron-3-embed-1b",
            "huggingface": "sentence-transformers/all-MiniLM-L6-v2",
            "google": "models/gemini-embedding-2-preview",
        }

        # Backward compatibility for old payloads that sent provider in embedding_model.
        if self.embedding_provider is None and self.embedding_model in default_model_by_provider:
            self.embedding_provider = self.embedding_model
            self.embedding_model = default_model_by_provider[self.embedding_provider]

        if self.embedding_provider is None:
            self.embedding_provider = "nvidia"

        if not self.embedding_model:
            self.embedding_model = default_model_by_provider[self.embedding_provider]

        self.collection_name = derive_collection_name(
            self.embedding_provider,
            self.embedding_model,
            self.chunk_strategy,
        )
        return self


class IndexRequest(BaseModel):
    document_id: Optional[uuid.UUID] = None
    document_ids: Optional[List[uuid.UUID]] = None
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
    evaluation: Optional[Dict[str, Any]] = None
    chunk_details: Optional[List[Dict[str, Any]]] = None


class CompareRequest(BaseModel):
    query: str
    configs: List[RAGConfig] = Field(..., min_length=1, max_length=4)
    include_evaluation: bool = False


class EvaluateCompareRequest(BaseModel):
    query: str
    results: List[ConfigResult] = Field(..., min_length=1, max_length=4)


class CompareResponse(BaseModel):
    query: str
    results: List[ConfigResult]

