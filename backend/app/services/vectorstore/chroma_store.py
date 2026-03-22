"""
Chroma vector store strategy.

Uses LangChain's Chroma wrapper to store and query vector embeddings.
"""

import os
import uuid
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from backend.app.services.chunking.base import Chunk
from backend.app.services.embedding.base import BaseEmbedder
from backend.app.services.vectorstore.base import BaseVectorStore

load_dotenv()


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
        return Chroma(
            collection_name=self.collection_name,
            embedding_function=embedding_function,
            persist_directory=self.persist_dir,
        )

    def add_chunks(self, chunks: List[Chunk], embedder: BaseEmbedder) -> None:
        if not chunks:
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
        Chroma.from_documents(
            documents=docs,
            embedding=adapter,
            collection_name=self.collection_name,
            persist_directory=self.persist_dir,
        )

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
