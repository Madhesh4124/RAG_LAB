from __future__ import annotations

import asyncio
from typing import List

from langchain_core.documents import Document

from app.compare.collection_registry import collection_exists, get_or_load_collection
from app.compare.schemas import IndexResponse, RAGConfig
from app.services.chunking.fixed_size import FixedSizeChunker
from app.services.chunking.recursive import RecursiveChunker
from app.services.chunking.semantic import SemanticChunker
from app.services.embedding.huggingface_api_embedder import HuggingFaceAPIEmbedder
from app.services.embedding.nvidia_embedder import NvidiaEmbedder


class _EmbeddingAdapter:
    def __init__(self, embedder):
        self.embedder = embedder

    def embed_documents(self, texts):
        if hasattr(self.embedder, "embed_batch"):
            return self.embedder.embed_batch(texts)
        return self.embedder.embed_documents(texts)

    def embed_query(self, text):
        if hasattr(self.embedder, "embed_text"):
            return self.embedder.embed_text(text)
        return self.embedder.embed_query(text)

    def embed_batch(self, texts):
        return self.embed_documents(texts)

    def embed_text(self, text):
        return self.embed_query(text)


def _load_embedder(embedding_model: str):
    if embedding_model == "nvidia":
        return NvidiaEmbedder(model="nvidia/nv-embed-v1")
    if embedding_model == "huggingface":
        try:
            from langchain_huggingface import HuggingFaceEmbeddings

            return _EmbeddingAdapter(HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2"))
        except Exception:
            return HuggingFaceAPIEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
    raise ValueError(f"Unsupported embedding model: {embedding_model}")


def _build_chunker(config: RAGConfig, embedder=None):
    if config.chunk_strategy == "fixed":
        return FixedSizeChunker()
    if config.chunk_strategy == "recursive":
        return RecursiveChunker()
    if config.chunk_strategy == "semantic":
        semantic_embedder = embedder if embedder is not None else _load_embedder(config.embedding_model)
        return SemanticChunker(embedder=semantic_embedder)
    raise ValueError(f"Unsupported chunk strategy: {config.chunk_strategy}")


def _chunk_count(vectorstore) -> int:
    try:
        return int(vectorstore._collection.count())
    except Exception:
        return 0


async def index_config(config: RAGConfig, document_text: str) -> IndexResponse:
    collection_name = config.collection_name

    if collection_exists(collection_name, config.embedding_model):
        return IndexResponse(
            config_name=config.name,
            collection_name=collection_name,
            chunk_count=_chunk_count(get_or_load_collection(collection_name, config.embedding_model)),
            status="already_exists",
        )

    def _index_sync() -> int:
        embedder = _load_embedder(config.embedding_model)
        chunker = _build_chunker(config, embedder if config.chunk_strategy == "semantic" else None)
        chunks = chunker.chunk(document_text, {"collection_name": collection_name})
        docs: List[Document] = []
        for idx, chunk in enumerate(chunks):
            metadata = dict(chunk.metadata or {})
            metadata.update(
                {
                    "chunk_index": idx,
                    "chunk_strategy": config.chunk_strategy,
                    "embedding_model": config.embedding_model,
                }
            )
            docs.append(Document(page_content=chunk.text, metadata=metadata))

        vectorstore = get_or_load_collection(collection_name, config.embedding_model)
        if docs:
            vectorstore.add_documents(docs)
        return len(docs)

    chunk_count = await asyncio.to_thread(_index_sync)
    return IndexResponse(
        config_name=config.name,
        collection_name=collection_name,
        chunk_count=chunk_count,
        status="success",
    )
