"""
RAG Pipeline.

Orchestrates the chunking, embedding, and vector storage components
into a single, unified workflow.
"""

import hashlib
from typing import Any, Dict, List, Tuple, Optional

from app.services.chunking.base import BaseChunker, Chunk
from app.services.embedding.base import BaseEmbedder
from app.services.vectorstore.base import BaseVectorStore
from app.services.retrieval.base import BaseRetriever
from app.services.llm.gemini_client import GeminiClient

# Memory dependencies
from app.services.memory.base import BaseMemory
from app.utils.timing import PipelineTimer


class RAGPipeline:
    """Unified RAG pipeline coordinating chunking, embedding, and storage.

    Args:
        chunker: The strategy to use for document chunking.
        embedder: The strategy to use for vectorizing chunks and queries.
        vectorstore: The storage strategy for indexing and retrieving chunks.
        memory: Optional memory module ensuring persistent conversation recall bounds natively.
    """

    def __init__(
        self,
        chunker: BaseChunker,
        embedder: BaseEmbedder,
        vectorstore: BaseVectorStore,
        memory: Optional[BaseMemory] = None,
        retriever: Optional[BaseRetriever] = None,
        llm_client: Optional[GeminiClient] = None,
        reranker: Optional[Any] = None,
    ) -> None:
        self.chunker = chunker
        self.embedder = embedder
        self.vectorstore = vectorstore
        self.memory = memory
        self.retriever = retriever
        self.llm_client = llm_client
        self.reranker = reranker
        self.timer = PipelineTimer()
        self._indexed_doc_ids = set()

    def index_document(self, text: str, doc_id: str, metadata: dict) -> None:
        """Processes a document and indexes it into the vector store.
        """
        if doc_id in self._indexed_doc_ids:
            return

        self.last_document_text = text
        self.last_document_id = doc_id
        self.last_document_metadata = metadata.copy() if metadata else {}
            
        self.timer.reset()
        
        enriched_metadata = metadata.copy() if metadata else {}
        enriched_metadata["doc_id"] = doc_id
        enriched_metadata["content_hash"] = hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()

        if hasattr(self.vectorstore, "is_document_indexed"):
            is_indexed = self.vectorstore.is_document_indexed(
                doc_id=doc_id,
                content_hash=enriched_metadata["content_hash"],
            )
            if is_indexed:
                return

        # 1. Chunk the document (Timed)
        self.timer.start("chunking_time_ms")
        chunks = self.chunker.chunk(text=text, metadata=enriched_metadata)
        self.timer.stop("chunking_time_ms")

        if hasattr(self.retriever, "index"):
            self.retriever.index(chunks)

        # 2. Embed and store the chunks (Timed)
        self.timer.start("embedding_time_ms")
        self.vectorstore.add_chunks(chunks=chunks, embedder=self.embedder)
        self.timer.stop("embedding_time_ms")
        self._indexed_doc_ids.add(doc_id)

    def retrieve(self, query: str, top_k: int = 5) -> List[Tuple[Chunk, float]]:
        """Retrieves chunks similar to the query.
        """
        # Time the active vector retrieval separately
        self.timer.start("retrieval_time_ms")
        
        if self.retriever:
            results = self.retriever.search(query=query, top_k=top_k)
        else:
            results = self.vectorstore.search(
                query=query, embedder=self.embedder, top_k=top_k
            )
            
        self.timer.stop("retrieval_time_ms")
        
        if self.reranker:
            self.timer.start("reranking_time_ms")
            results = self.reranker.rerank(query, results, top_k)
            self.timer.stop("reranking_time_ms")
            
        return results

    def generate(self, query: str, chunks: List[Any], llm_client: Optional[GeminiClient] = None) -> str:
        """Generation bridge wrapping contexts dynamically before pinging any LLM native interfaces."""
        self.timer.start("llm_time_ms")
        
        target_llm = llm_client or self.llm_client
        
        if target_llm:
            if self.memory and hasattr(self.memory, "get") and self.memory.get():
                answer = target_llm.generate_with_memory(
                    query=query, 
                    chunks=chunks, 
                    memory=self.memory
                )
            else:
                answer = target_llm.generate(query=query, chunks=chunks)
        else:
            answer = f"Simulated Response to Query: [{query}]"
        
        if self.memory:
            self.memory.add_interaction(query, answer)
            
        self.timer.stop("llm_time_ms")
        return answer

    def generate_stream(self, query: str, chunks: List[Any], llm_client: Optional[GeminiClient] = None):
        """Stream version of generate."""
        target_llm = llm_client or self.llm_client
        if not target_llm:
            yield "LLM Client not initialized."
            return

        full_response = ""
        if self.memory and hasattr(self.memory, "get") and self.memory.get():
            iterator = target_llm.generate_stream_with_memory(query, chunks, self.memory)
        else:
            iterator = target_llm.generate_stream(query, chunks)

        for chunk_text in iterator:
            piece = chunk_text if isinstance(chunk_text, str) else str(chunk_text)
            full_response += piece
            yield piece

        if self.memory:
            self.memory.add_interaction(query, full_response)
        
    def get_last_timings(self) -> Dict[str, float]:
        """Returns the PipelineTimer's latest metrics dict spanning strictly active pipeline schema domains natively."""
        return self.timer.to_metrics_dict()

    def get_config(self) -> Dict[str, Any]:
        """Returns the fully assembled pipeline configuration.
        """
        config = {
            "chunker": self.chunker.get_config(),
            "embedder": self.embedder.get_config(),
            "vectorstore": self.vectorstore.get_config(),
        }
        if self.memory:
            config["memory"] = self.memory.get_config() if hasattr(self.memory, "get_config") else "custom_memory"
        if self.retriever:
            config["retriever"] = self.retriever.get_config() if hasattr(self.retriever, "get_config") else "custom_retriever"
        if self.llm_client:
            config["llm"] = self.llm_client.get_config() if hasattr(self.llm_client, "get_config") else "custom_llm"
        if getattr(self, "reranker", None):
            config["reranker"] = self.reranker.get_config() if hasattr(self.reranker, "get_config") else "custom_reranker"
            
        return config
