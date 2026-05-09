"""Sparse BM25 Retriever implementation with disk-based corpus persistence (P1.4).

The BM25 index is rebuilt from the persisted corpus on creation, so it survives
server restarts without requiring a full re-index from Chroma.

Cache location: {CHROMA_PERSIST_DIR}/bm25_{collection_name}.json
Controlled by: CHROMA_PERSIST_DIR env-var (defaults to ./chroma_db).
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rank_bm25 import BM25Okapi

from app.services.chunking.base import Chunk
from app.services.retrieval.base import BaseRetriever

logger = logging.getLogger(__name__)

_CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")


class BM25Retriever(BaseRetriever):
    """BM25 sparse retriever with optional disk-backed corpus cache."""

    def __init__(
        self,
        chunks: Optional[List[Chunk]] = None,
        collection_name: Optional[str] = None,
    ):
        self.chunks: List[Chunk] = []
        self.bm25: Optional[BM25Okapi] = None
        self._collection_name = collection_name

        # Auto-restore from disk cache if available (P1.4).
        if collection_name:
            self._load_cache()

        if chunks:
            self.index(chunks)

    # ------------------------------------------------------------------
    # Disk cache helpers
    # ------------------------------------------------------------------

    def _cache_path(self) -> Optional[Path]:
        if not self._collection_name:
            return None
        return Path(_CHROMA_PERSIST_DIR) / f"bm25_{self._collection_name}.json"

    def _save_cache(self) -> None:
        """Persist the current corpus to disk so it survives restarts."""
        path = self._cache_path()
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = [
                {"text": chunk.text, "metadata": getattr(chunk, "metadata", {})}
                for chunk in self.chunks
            ]
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            logger.debug("BM25Retriever: saved %d chunks to cache '%s'", len(self.chunks), path)
        except Exception:
            logger.warning("BM25Retriever: failed to save cache to '%s'", path, exc_info=True)

    def _load_cache(self) -> None:
        """Restore corpus from disk cache and rebuild the BM25 index."""
        path = self._cache_path()
        if path is None or not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, list) or not data:
                return
            restored: List[Chunk] = []
            for item in data:
                chunk = Chunk(
                    text=item["text"],
                    metadata=item.get("metadata", {}),
                )
                restored.append(chunk)
            self.chunks = restored
            tokenized_corpus = [chunk.text.split() for chunk in self.chunks]
            self.bm25 = BM25Okapi(tokenized_corpus)
            logger.info(
                "BM25Retriever: restored %d chunks from cache '%s'",
                len(self.chunks),
                path,
            )
        except Exception:
            logger.warning(
                "BM25Retriever: failed to load cache from '%s'; starting fresh",
                path,
                exc_info=True,
            )
            self.chunks = []
            self.bm25 = None

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def index(self, chunks: List[Chunk]) -> None:
        if not chunks:
            return

        self.chunks.extend(chunks)
        # Rebuild BM25 index over the full accumulated corpus.
        tokenized_corpus = [chunk.text.split() for chunk in self.chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)
        # Persist updated corpus to disk (P1.4).
        self._save_cache()

    def search(self, query: str, top_k: int) -> List[Tuple[Chunk, float]]:
        if not self.chunks or self.bm25 is None:
            return []

        tokenized_query = query.split()
        scores = self.bm25.get_scores(tokenized_query)

        max_score = max(scores) if len(scores) > 0 else 0.0

        if max_score == 0.0:
            return []

        # Pair chunks with scores
        chunk_scores = list(zip(self.chunks, scores))

        # Sort by score descending
        chunk_scores.sort(key=lambda x: x[1], reverse=True)

        # Normalize scores in 0-1 range and limit to top_k
        results = []
        for chunk, score in chunk_scores[:top_k]:
            normalized_score = score / max_score
            results.append((chunk, normalized_score))

        return results

    def get_config(self) -> Dict[str, Any]:
        return {"strategy": "bm25", "collection_name": self._collection_name}
