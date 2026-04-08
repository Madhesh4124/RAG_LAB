from __future__ import annotations

import asyncio
from typing import List

from langchain_core.documents import Document

from app.compare.collection_registry import collection_exists, get_or_load_collection
from app.compare.schemas import IndexResponse, RAGConfig
from app.services.pipeline_factory import PipelineFactory
from app.services.embedding.base import BaseEmbedder


def _load_embedder(embedding_provider: str, embedding_model: str) -> BaseEmbedder:
    return PipelineFactory.create_embedder(
        {
            "provider": embedding_provider,
            "model": embedding_model,
        }
    )


def _build_chunker(config: RAGConfig, embedder=None):
    chunk_cfg = dict(config.chunk_params or {})
    chunk_cfg["type"] = config.chunk_strategy

    if config.chunk_strategy == "semantic":
        semantic_embedder = embedder if embedder is not None else _load_embedder(
            config.embedding_provider,
            config.embedding_model,
        )
        return PipelineFactory.create_chunker(chunk_cfg, embedder=semantic_embedder)

    return PipelineFactory.create_chunker(chunk_cfg)


def _chunk_count(vectorstore) -> int:
    try:
        return int(vectorstore._collection.count())
    except Exception:
        return 0


async def index_config(
    config: RAGConfig,
    document_text: str,
    user_scope: str | None = None,
) -> IndexResponse:
    collection_name = config.collection_name

    if collection_exists(
        collection_name,
        config.embedding_provider,
        config.embedding_model,
        user_scope=user_scope,
    ):
        return IndexResponse(
            config_name=config.name,
            collection_name=collection_name,
            chunk_count=_chunk_count(
                get_or_load_collection(
                    collection_name,
                    config.embedding_provider,
                    config.embedding_model,
                    user_scope=user_scope,
                )
            ),
            status="already_exists",
        )

    def _index_sync() -> int:
        embedder = _load_embedder(config.embedding_provider, config.embedding_model)
        chunker = _build_chunker(config, embedder if config.chunk_strategy == "semantic" else None)
        chunks = chunker.chunk(document_text, {"collection_name": collection_name})
        docs: List[Document] = []
        for idx, chunk in enumerate(chunks):
            metadata = dict(chunk.metadata or {})
            metadata.update(
                {
                    "chunk_index": idx,
                    "chunk_strategy": config.chunk_strategy,
                    "embedding_provider": config.embedding_provider,
                    "embedding_model": config.embedding_model,
                }
            )
            docs.append(Document(page_content=chunk.text, metadata=metadata))

        vectorstore = get_or_load_collection(
            collection_name,
            config.embedding_provider,
            config.embedding_model,
            user_scope=user_scope,
        )
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
