from __future__ import annotations

import importlib
import shutil
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv(override=True)

def _load_chroma_class():
    try:
        return importlib.import_module("langchain_chroma").Chroma
    except Exception:  # pragma: no cover - compatibility fallback
        return importlib.import_module("langchain_community.vectorstores").Chroma


Chroma = _load_chroma_class()

from app.services.embedding.huggingface_api_embedder import HuggingFaceAPIEmbedder
from app.services.embedding.nvidia_embedder import NvidiaEmbedder

_registry: Dict[str, Any] = {}
_PERSIST_DIR = Path(__file__).resolve().parents[2] / "chroma_store"


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
        return _EmbeddingAdapter(NvidiaEmbedder(model="nvidia/nv-embed-v1"))
    if embedding_model == "huggingface":
        try:
            from langchain_huggingface import HuggingFaceEmbeddings

            return _EmbeddingAdapter(HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2"))
        except Exception:
            return _EmbeddingAdapter(HuggingFaceAPIEmbedder(model="sentence-transformers/all-MiniLM-L6-v2"))
    raise ValueError(f"Unsupported embedding model: {embedding_model}")


def get_or_load_collection(collection_name: str, embedding_model: str) -> Any:
    if collection_name not in _registry:
        embedder = _load_embedder(embedding_model)
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embedder,
            persist_directory=str(_PERSIST_DIR),
        )
        _registry[collection_name] = vectorstore
    return _registry[collection_name]


def collection_exists(collection_name: str, embedding_model: str = "nvidia") -> bool:
    try:
        vectorstore = get_or_load_collection(collection_name, embedding_model)
        return int(vectorstore._collection.count()) > 0
    except Exception:
        return False


def clear_collection_registry() -> None:
    _registry.clear()


def clear_compare_chroma_store() -> None:
    clear_collection_registry()
    if _PERSIST_DIR.exists():
        shutil.rmtree(_PERSIST_DIR, ignore_errors=True)
    _PERSIST_DIR.mkdir(parents=True, exist_ok=True)
