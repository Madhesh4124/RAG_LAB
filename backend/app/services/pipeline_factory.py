"""
Factory for assembling RAG pipelines.

Takes configuration dictionaries and dynamically initializes
the concrete implementations for chunking, embedding, and vector storage.
"""

from typing import Any, Dict

from app.services.chunking.base import BaseChunker
from app.services.embedding.base import BaseEmbedder
from app.services.vectorstore.base import BaseVectorStore
from app.services.rag_pipeline import RAGPipeline


class PipelineFactory:
    """Factory to create RAG pipelines dynamically from configurations."""

    @staticmethod
    def create_chunker(config: Dict[str, Any]) -> BaseChunker:
        """Create a chunker dynamically based on the configuration."""
        kwargs = config.copy()
        strategy = kwargs.pop("type", None)

        # Backward-compat normalization for semantic chunking configs:
        # frontend presets use `chunk_size`, while SemanticChunker expects
        # `max_chunk_size`. It also does not support `overlap`.
        if strategy == "semantic":
            if "max_chunk_size" not in kwargs and "chunk_size" in kwargs:
                kwargs["max_chunk_size"] = kwargs.pop("chunk_size")
            else:
                kwargs.pop("chunk_size", None)
            kwargs.pop("overlap", None)

        if strategy == "fixed_size":
            from app.services.chunking.fixed_size import FixedSizeChunker
            return FixedSizeChunker(**kwargs)
        elif strategy == "semantic":
            from app.services.chunking.semantic import SemanticChunker
            return SemanticChunker(**kwargs)
        elif strategy == "chapter":
            from app.services.chunking.chapter import ChapterChunker
            return ChapterChunker(**kwargs)
        elif strategy == "recursive":
            from app.services.chunking.recursive import RecursiveChunker
            return RecursiveChunker(**kwargs)
        elif strategy == "regex":
            from app.services.chunking.regex_chunker import RegexChunker
            return RegexChunker(**kwargs)
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")

    @staticmethod
    def create_embedder(config: Dict[str, Any]) -> BaseEmbedder:
        """Create an embedder dynamically based on the configuration."""
        provider = config.get("provider")
        model = config.get("model")

        # Setup kwargs specifically for the requested model argument
        kwargs = {}
        if model is not None:
            kwargs["model"] = model

        if provider == "google":
            from app.services.embedding.google_embedder import GoogleEmbedder
            return GoogleEmbedder(**kwargs)
        elif provider == "nvidia":
            from app.services.embedding.nvidia_embedder import NvidiaEmbedder
            return NvidiaEmbedder(**kwargs)
        elif provider == "huggingface":
            from app.services.embedding.huggingface_api_embedder import HuggingFaceAPIEmbedder
            return HuggingFaceAPIEmbedder(**kwargs)
        else:
            raise ValueError(f"Unknown embedding provider: {provider}")

    @staticmethod
    def create_vectorstore(config: Dict[str, Any]) -> BaseVectorStore:
        """Create a vector store dynamically based on the configuration."""
        kwargs = config.copy()
        strategy = kwargs.pop("type", None)

        if strategy == "chroma":
            from app.services.vectorstore.chroma_store import ChromaStore
            return ChromaStore(**kwargs)
        elif strategy == "faiss":
            from app.services.vectorstore.faiss_store import FAISSStore
            return FAISSStore(**kwargs)
        else:
            raise ValueError(f"Unknown vectorstore strategy: {strategy}")

    @staticmethod
    def create_retriever(config: Dict[str, Any], vectorstore: BaseVectorStore, embedder: BaseEmbedder) -> Any:
        """Create a retriever dynamically based on the configuration."""
        if not config:
            return None
            
        type_ = config.get("type")
        
        if type_ == "hybrid":
            from app.services.retrieval.dense_retriever import DenseRetriever
            from app.services.retrieval.sparse_retriever import BM25Retriever
            from app.services.retrieval.hybrid_retriever import HybridRetriever
            dr = DenseRetriever(vectorstore, embedder)
            
            # chunks can be loaded or passed from config
            chunks = config.get("chunks", [])
            sr = BM25Retriever(chunks)
            alpha = config.get("alpha", 0.7)
            return HybridRetriever(dense_retriever=dr, sparse_retriever=sr, alpha=alpha)
            
        elif type_ == "dense":
            from app.services.retrieval.dense_retriever import DenseRetriever
            return DenseRetriever(vectorstore, embedder)
            
        elif type_ == "sparse":
            from app.services.retrieval.sparse_retriever import BM25Retriever
            chunks = config.get("chunks", [])
            return BM25Retriever(chunks)
            
        else:
            return None

    @staticmethod
    def create_llm_client(config: Dict[str, Any]) -> Any:
        """Create an LLM client dynamically based on the configuration."""
        if not config:
            return None
            
        provider = config.get("provider")
        if provider == "gemini":
            from app.services.llm.gemini_client import GeminiClient
            model = config.get("model", "gemini-2.5-flash")
            temperature = config.get("temperature", 0.2)
            return GeminiClient(model=model, temperature=temperature)
            
        return None

    @staticmethod
    def create_pipeline(config: Dict[str, Any]) -> RAGPipeline:
        """Assemble a complete RAG pipeline from a nested configuration.

        Args:
            config: A dictionary containing 'chunker', 'embedder', and
                    'vectorstore' configuration keys.

        Returns:
            A fully initialized RAGPipeline instance.
        """
        chunker_cfg = config.get("chunker", {})
        embedder_cfg = config.get("embedder", {})
        vectorstore_cfg = config.get("vectorstore", {})

        chunker = PipelineFactory.create_chunker(chunker_cfg)
        embedder = PipelineFactory.create_embedder(embedder_cfg)
        vectorstore = PipelineFactory.create_vectorstore(vectorstore_cfg)

        retriever = PipelineFactory.create_retriever(config.get("retriever", {}), vectorstore, embedder)
        llm_client = PipelineFactory.create_llm_client(config.get("llm", {}))

        return RAGPipeline(
            chunker=chunker,
            embedder=embedder,
            vectorstore=vectorstore,
            retriever=retriever,
            llm_client=llm_client
        )
