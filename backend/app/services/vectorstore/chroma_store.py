"""
Chroma vector store strategy.

Uses LangChain's Chroma wrapper to store and query vector embeddings.
"""

import os
import uuid
import warnings
from typing import Any, Dict, List, Tuple

from chromadb.config import Settings
from dotenv import load_dotenv
from langchain_core.documents import Document

load_dotenv()

# Disable noisy Chroma telemetry by default in local/dev runs.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "FALSE")
os.environ.setdefault("CHROMA_TELEMETRY_IMPL", "none")

try:
    from langchain_chroma import Chroma
except Exception:  # pragma: no cover - compatibility fallback
    warnings.filterwarnings(
        "ignore",
        message=r".*The class `Chroma` was deprecated in LangChain.*",
    )
    from langchain_community.vectorstores import Chroma

from app.services.chunking.base import Chunk
from app.services.embedding.base import BaseEmbedder
from app.services.vectorstore.base import BaseVectorStore

class _EmbedderAdapter:
    """Adapter to make BaseEmbedder compatible with LangChain's Embeddings."""

    def __init__(self, embedder: BaseEmbedder) -> None:
        self.embedder = embedder

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embedder.embed_batch(texts)

    def embed_query(self, text: str) -> List[float]:
        return self.embedder.embed_text(text)


class ChromaStore(BaseVectorStore):
    """Chroma vector store implementation.

    Args:
        collection_name: Name of the Chroma collection.
                         Defaults to "rag_collection".
    """

    def __init__(self, collection_name: str = "rag_collection") -> None:
        self.collection_name = collection_name
        self.persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

    def _get_vectorstore(self, embedder: BaseEmbedder = None) -> Chroma:
        embedding_function = _EmbedderAdapter(embedder) if embedder else None
        chroma_settings = Settings(anonymized_telemetry=False)
        return Chroma(
            collection_name=self.collection_name,
            embedding_function=embedding_function,
            persist_directory=self.persist_dir,
            client_settings=chroma_settings,
        )

    def add_chunks(self, chunks: List[Chunk], embedder: BaseEmbedder) -> None:
        if not chunks:
            return

        first_meta = chunks[0].metadata or {}
        doc_id = first_meta.get("doc_id")
        content_hash = first_meta.get("content_hash")
        if doc_id and self.is_document_indexed(doc_id=doc_id, content_hash=content_hash):
            return

        docs = []
        for chunk in chunks:
            meta = chunk.metadata.copy() if chunk.metadata else {}
            meta["chunk_id"] = str(chunk.id)
            meta["start_char"] = chunk.start_char
            meta["end_char"] = chunk.end_char

            if "doc_id" not in meta:
                meta["doc_id"] = "unknown_doc"

            doc = Document(page_content=chunk.text, metadata=meta)
            docs.append(doc)

        adapter = _EmbedderAdapter(embedder)
        chroma_settings = Settings(anonymized_telemetry=False)
        Chroma.from_documents(
            documents=docs,
            embedding=adapter,
            collection_name=self.collection_name,
            persist_directory=self.persist_dir,
            client_settings=chroma_settings,
        )

    def is_document_indexed(self, doc_id: str, content_hash: str | None = None) -> bool:
        where: Dict[str, Any] = {"doc_id": doc_id}
        if content_hash:
            where["content_hash"] = content_hash

        try:
            vs = self._get_vectorstore()
            found = vs._collection.get(where=where, limit=1)
            ids = found.get("ids", []) if isinstance(found, dict) else []
            return bool(ids)
        except Exception:
            return False

    def search(
        self, query: str, embedder: BaseEmbedder, top_k: int = 5
    ) -> List[Tuple[Chunk, float]]:
        vs = self._get_vectorstore(embedder)
        results = vs.similarity_search_with_score(query, k=top_k)

        parsed_results = []
        for doc, score in results:
            meta = doc.metadata.copy()
            chunk_id_str = meta.pop("chunk_id", str(uuid.uuid4()))
            start_char = meta.pop("start_char", 0)
            end_char = meta.pop("end_char", 0)

            chunk = Chunk(
                id=uuid.UUID(chunk_id_str) if isinstance(chunk_id_str, str) else chunk_id_str,
                text=doc.page_content,
                metadata=meta,
                start_char=start_char,
                end_char=end_char,
            )
            parsed_results.append((chunk, float(score)))

        return parsed_results

    def delete_document(self, doc_id: str) -> None:
        vs = self._get_vectorstore()
        try:
            vs._collection.delete(where={"doc_id": doc_id})
        except Exception:
            # Depending on Chroma's version and state, this might fail silently
            # or throw an error if the collection doesn't exist yet.
            pass

    def get_config(self) -> Dict[str, Any]:
        return {
            "strategy": "chroma",
            "collection_name": self.collection_name,
            "persist_dir": self.persist_dir,
        }
