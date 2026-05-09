import os
import uuid
import logging
from typing import List, Dict, Any

from langchain_core.documents import Document
from app.services.vectorstore.base import BaseVectorStore
from app.services.embedding.base import BaseEmbedder
from app.models.chunk import Chunk

logger = logging.getLogger(__name__)

class QdrantStore(BaseVectorStore):
    """Qdrant vector store implementation (P3.5).
    
    Supports multi-tenancy inherently. Each config gets its own collection,
    or we can use a single collection with user_id payload filters.
    Here we implement the collection-per-config approach to match Chroma behavior.
    """

    def __init__(self, collection_name: str, config: Dict[str, Any] = None):
        super().__init__(collection_name, config)
        try:
            from qdrant_client import QdrantClient
        except ImportError:
            raise ImportError("Qdrant backend requires 'qdrant-client' and 'langchain-qdrant'.")
            
        # URL defaults to local, can be overridden by env
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_api_key = os.getenv("QDRANT_API_KEY", None)
        
        self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        self.collection_name = collection_name
        self._store = None

    def _get_or_create_store(self, embedder: BaseEmbedder):
        if self._store is not None:
            return self._store

        from langchain_qdrant import QdrantVectorStore

        class _EmbedderAdapter:
            def __init__(self, embedder: BaseEmbedder):
                self.embedder = embedder
            def embed_documents(self, texts: List[str]) -> List[List[float]]:
                return self.embedder.embed_in_batches(texts)
            def embed_query(self, text: str) -> List[float]:
                return self.embedder.embed_text(text)

        self._store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embedding=_EmbedderAdapter(embedder)
        )
        return self._store

    def add_chunks(self, chunks: List[Chunk], embedder: BaseEmbedder) -> None:
        if not chunks:
            return
            
        store = self._get_or_create_store(embedder)
        
        docs = []
        for chunk in chunks:
            metadata = chunk.metadata or {}
            metadata["id"] = chunk.id
            docs.append(Document(page_content=chunk.text, metadata=metadata))
            
        # QdrantVectorStore supports batch addition natively, but our _EmbedderAdapter
        # handles the embed_in_batches logic securely.
        store.add_documents(docs)

    def search(
        self, query: str, embedder: BaseEmbedder, top_k: int = 5, filter_dict: Dict[str, Any] = None
    ) -> List[Chunk]:
        store = self._get_or_create_store(embedder)
        
        # In langchain-qdrant, filter_dict can be directly passed as qdrant Filter 
        # or simplified dict. Here we pass a simple dict if supported.
        kwargs = {"k": top_k}
        if filter_dict:
            from qdrant_client.http import models as rest
            filters = []
            for k, v in filter_dict.items():
                filters.append(rest.FieldCondition(key=k, match=rest.MatchValue(value=v)))
            kwargs["filter"] = rest.Filter(must=filters)
            
        results = store.similarity_search_with_score(query, **kwargs)
        
        chunks = []
        for doc, score in results:
            chunks.append(Chunk(
                id=doc.metadata.get("id", str(uuid.uuid4())),
                text=doc.page_content,
                metadata=doc.metadata,
                score=float(score)
            ))
        return chunks

    def clear(self) -> None:
        try:
            self.client.delete_collection(self.collection_name)
        except Exception as e:
            logger.warning("Failed to delete Qdrant collection %s: %s", self.collection_name, e)

    def is_document_indexed(self, doc_id: str) -> bool:
        try:
            from qdrant_client.http import models as rest
            # Check if collection exists
            if not self.client.collection_exists(self.collection_name):
                return False
                
            res = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=rest.Filter(
                    must=[
                        rest.FieldCondition(
                            key="doc_id",
                            match=rest.MatchValue(value=doc_id)
                        )
                    ]
                ),
                limit=1,
                with_payload=False,
                with_vectors=False
            )
            return len(res[0]) > 0
        except Exception:
            return False
