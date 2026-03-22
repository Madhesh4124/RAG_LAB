"""
RAG Pipeline.

Orchestrates the chunking, embedding, and vector storage components
into a single, unified workflow.
"""

from typing import Any, Dict, List, Tuple, Optional

from backend.app.services.chunking.base import BaseChunker, Chunk
from backend.app.services.embedding.base import BaseEmbedder
from backend.app.services.vectorstore.base import BaseVectorStore
from backend.app.services.retrieval.base import BaseRetriever
from backend.app.services.llm.gemini_client import GeminiClient

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
    ) -> None:
        self.chunker = chunker
        self.embedder = embedder
        self.vectorstore = vectorstore
        self.memory = memory
        self.retriever = retriever
        self.llm_client = llm_client
        self.timer = PipelineTimer()

    def index_document(self, text: str, doc_id: str, metadata: dict) -> None:
        """Processes a document and indexes it into the vector store.
        """
        self.timer.reset()
        
        enriched_metadata = metadata.copy() if metadata else {}
        enriched_metadata["doc_id"] = doc_id

        # 1. Chunk the document (Timed)
        self.timer.start("chunking_time_ms")
        chunks = self.chunker.chunk(text=text, metadata=enriched_metadata)
        self.timer.stop("chunking_time_ms")

        # 2. Embed and store the chunks (Timed)
        self.timer.start("embedding_time_ms")
        self.vectorstore.add_chunks(chunks=chunks, embedder=self.embedder)
        self.timer.stop("embedding_time_ms")

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
        return results

    def generate(self, query: str, chunks: List[Any], llm_client: Optional[GeminiClient] = None) -> str:
        """Generation bridge wrapping contexts dynamically before pinging any LLM native interfaces."""
        self.timer.start("llm_time_ms")
        
        target_llm = llm_client or self.llm_client
        
        if target_llm:
            if self.memory and self.memory.get_context():
                answer = target_llm.generate_with_memory(
                    query=query, 
                    chunks=chunks, 
                    context=self.memory.get_context()
                )
            else:
                answer = target_llm.generate(query=query, chunks=chunks)
        else:
            # Fallback when no LLM client is set
            answer = f"Simulated Response to Query: [{query}] mapped using attached memory."
        
        # Keep sliding memory actively aware of the outbound reply context natively
        if self.memory:
            self.memory.add_interaction(query, answer)
            
        self.timer.stop("llm_time_ms")
        return answer
        
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
            
        return config
