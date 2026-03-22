"""
FAISS vector store strategy.

Uses LangChain's FAISS wrapper to store and query vector embeddings.
"""

import uuid
from typing import Any, Dict, List, Tuple

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from backend.app.services.chunking.base import Chunk
from backend.app.services.embedding.base import BaseEmbedder
from backend.app.services.vectorstore.base import BaseVectorStore


class _EmbedderAdapter:
    """Adapter to make BaseEmbedder compatible with LangChain's Embeddings."""

    def __init__(self, embedder: BaseEmbedder) -> None:
        self.embedder = embedder

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embedder.embed_batch(texts)

    def embed_query(self, text: str) -> List[float]:
        return self.embedder.embed_text(text)


class FAISSStore(BaseVectorStore):
    """FAISS vector store implementation.

    Note:
        FAISS is an in-memory only vector store in this configuration.
        Data added via `add_chunks()` is lost on application restart,
        making this store best suited for rapid experimentation and
        speed comparison rather than persistent storage.

    Args:
        index_name: Name of the FAISS index. Defaults to "rag_index".
    """

    def __init__(self, index_name: str = "rag_index") -> None:
        self.index_name = index_name
        self.vectorstore: FAISS = None

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
        new_vs = FAISS.from_documents(docs, adapter)

        if self.vectorstore is None:
            self.vectorstore = new_vs
        else:
            self.vectorstore.merge_from(new_vs)

    def search(
        self, query: str, embedder: BaseEmbedder, top_k: int = 5
    ) -> List[Tuple[Chunk, float]]:
        if self.vectorstore is None:
            return []

        # FAISS search doesn't require us to re-pass the embedding function explicitly here
        # since FAISS stores the embedding_function from initialization wrapper.
        results = self.vectorstore.similarity_search_with_score(query, k=top_k)

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
            # L2 distance is returned by FAISS default (lower is better contextually, 
            # though it depends on distance metrics chosen initially).
            parsed_results.append((chunk, float(score)))

        return parsed_results

    def delete_document(self, doc_id: str) -> None:
        if self.vectorstore is None:
            return

        ids_to_delete = []
        # Access internal docstore to filter out metadata for precise document deletion
        for _id, doc in self.vectorstore.docstore._dict.items():
            if doc.metadata.get("doc_id") == doc_id:
                ids_to_delete.append(_id)

        if ids_to_delete:
            self.vectorstore.delete(ids_to_delete)

    def get_config(self) -> Dict[str, Any]:
        return {
            "strategy": "faiss",
            "index_name": self.index_name,
        }
