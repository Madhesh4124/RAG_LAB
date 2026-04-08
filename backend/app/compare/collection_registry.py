from __future__ import annotations

import importlib
import os
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any

from chromadb import PersistentClient
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
from app.compare.summary_registry import clear_summary_registry

def _resolve_persist_dir() -> Path:
    candidates = [
        os.getenv("CHROMA_PERSIST_DIR", "").strip(),
        "/data/chroma_store",
        str(Path(tempfile.gettempdir()) / "rag_lab_compare_chroma_store"),
    ]

    seen = set()
    for candidate in candidates:
        if not candidate:
            continue
        candidate_path = Path(candidate).resolve()
        if str(candidate_path) in seen:
            continue
        seen.add(str(candidate_path))
        try:
            candidate_path.mkdir(parents=True, exist_ok=True)
            probe = candidate_path / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return candidate_path
        except Exception:
            continue

    fallback = Path(__file__).resolve().parents[2] / "chroma_store"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


_PERSIST_DIR = _resolve_persist_dir()
_EMBEDDER_CACHE: dict[tuple[str, str], "_EmbeddingAdapter"] = {}
_EMBEDDER_CACHE_LOCK = threading.Lock()
_CLIENT_CACHE: dict[str, Any] = {}
_CLIENT_CACHE_LOCK = threading.Lock()


def _scoped_collection_name(collection_name: str, user_scope: str | None = None) -> str:
    if not user_scope:
        return collection_name
    return f"user_{user_scope}_{collection_name}"


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


def _load_embedder(embedding_provider: str, embedding_model: str):
    cache_key = (embedding_provider, embedding_model)
    with _EMBEDDER_CACHE_LOCK:
        cached = _EMBEDDER_CACHE.get(cache_key)
    if cached is not None:
        return cached

    if embedding_provider == "nvidia":
        model_name = embedding_model or "nvidia/nv-embed-v1"
        embedder = _EmbeddingAdapter(NvidiaEmbedder(model=model_name))
    elif embedding_provider == "huggingface":
        model_name = embedding_model or "sentence-transformers/all-MiniLM-L6-v2"
        try:
            from langchain_huggingface import HuggingFaceEmbeddings

            embedder = _EmbeddingAdapter(HuggingFaceEmbeddings(model_name=model_name))
        except Exception:
            embedder = _EmbeddingAdapter(HuggingFaceAPIEmbedder(model=model_name))
    else:
        raise ValueError(f"Unsupported embedding provider: {embedding_provider}")

    with _EMBEDDER_CACHE_LOCK:
        _EMBEDDER_CACHE.setdefault(cache_key, embedder)
        return _EMBEDDER_CACHE[cache_key]


def _get_cached_client(persist_dir: Path):
    cache_key = str(persist_dir.resolve())
    with _CLIENT_CACHE_LOCK:
        cached = _CLIENT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    client = PersistentClient(path=cache_key)
    with _CLIENT_CACHE_LOCK:
        _CLIENT_CACHE.setdefault(cache_key, client)
        return _CLIENT_CACHE[cache_key]


def get_or_load_collection(
    collection_name: str,
    embedding_provider: str,
    embedding_model: str,
    user_scope: str | None = None,
) -> Any:
    scoped_collection_name = _scoped_collection_name(collection_name, user_scope)
    embedder = _load_embedder(embedding_provider, embedding_model)
    return Chroma(
        collection_name=scoped_collection_name,
        embedding_function=embedder,
        client=_get_cached_client(_PERSIST_DIR),
    )


def collection_exists(
    collection_name: str,
    embedding_provider: str = "nvidia",
    embedding_model: str = "nvidia/nv-embed-v1",
    user_scope: str | None = None,
) -> bool:
    try:
        vectorstore = get_or_load_collection(collection_name, embedding_provider, embedding_model, user_scope=user_scope)
        return int(vectorstore._collection.count()) > 0
    except Exception:
        return False


def clear_collection_registry() -> None:
    with _EMBEDDER_CACHE_LOCK:
        _EMBEDDER_CACHE.clear()
    with _CLIENT_CACHE_LOCK:
        _CLIENT_CACHE.clear()
    return None


def clear_compare_chroma_store() -> None:
    clear_collection_registry()
    clear_summary_registry()
    if _PERSIST_DIR.exists():
        shutil.rmtree(_PERSIST_DIR, ignore_errors=True)
    _PERSIST_DIR.mkdir(parents=True, exist_ok=True)
