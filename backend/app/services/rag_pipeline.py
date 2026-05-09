"""RAG pipeline orchestration.

The pipeline remains responsible for chunking, retrieval, and generation, but
it no longer keeps request/user state that could leak across requests.
"""

import asyncio
import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Tuple, Optional

from app.services.chunking.base import BaseChunker, Chunk
from app.services.embedding.base import BaseEmbedder
from app.services.vectorstore.base import BaseVectorStore
from app.services.retrieval.base import BaseRetriever
from app.services.llm.gemini_client import GeminiClient

# Memory dependencies
from app.services.memory.base import BaseMemory
from app.utils.timing import PipelineTimer

logger = logging.getLogger(__name__)


def _stable_config_fingerprint(config: Dict[str, Any]) -> str:
    try:
        payload = json.dumps(config or {}, sort_keys=True, default=str)
    except TypeError:
        payload = str(config or {})
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


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
        rerank_fetch_k: int = 20,
    ) -> None:
        self.chunker = chunker
        self.embedder = embedder
        self.vectorstore = vectorstore
        self.memory = memory
        self.retriever = retriever
        self.llm_client = llm_client
        self.reranker = reranker
        self.rerank_fetch_k = max(1, int(rerank_fetch_k))
        self.timer = PipelineTimer()

    def index_document(self, text: str, doc_id: str, metadata: dict) -> None:
        """Processes a document and indexes it into the vector store.
        """
        timer = PipelineTimer()

        enriched_metadata = metadata.copy() if metadata else {}
        enriched_metadata["doc_id"] = doc_id
        enriched_metadata["chunker_fingerprint"] = _stable_config_fingerprint(self.chunker.get_config())
        enriched_metadata["content_hash"] = hashlib.sha256(
            f"{enriched_metadata['chunker_fingerprint']}:{text}".encode("utf-8")
        ).hexdigest()

        # Check if the vectorstore already has it
        is_indexed = False
        if hasattr(self.vectorstore, "is_document_indexed"):
            is_indexed = self.vectorstore.is_document_indexed(
                doc_id=doc_id,
                content_hash=enriched_metadata["content_hash"],
            )

        # Check if we have an in-memory retriever (like BM25) that lost its chunks due to server restart
        retriever_needs_index = False
        if hasattr(self.retriever, "index"):
            if hasattr(self.retriever, "chunks") and not self.retriever.chunks:
                retriever_needs_index = True
            elif hasattr(self.retriever, "sparse_retriever") and hasattr(self.retriever.sparse_retriever, "chunks") and not getattr(self.retriever.sparse_retriever, "chunks"):
                retriever_needs_index = True

        if is_indexed and not retriever_needs_index:
            return

        # 1. Chunk the document (Timed)
        timer.start("chunking_time_ms")
        chunks = self.chunker.chunk(text=text, metadata=enriched_metadata)
        timer.stop("chunking_time_ms")

        if hasattr(self.retriever, "index"):
            self.retriever.index(chunks)

        # 2. Embed and store the chunks (Timed)
        if not is_indexed:
            timer.start("embedding_time_ms")
            self.vectorstore.add_chunks(chunks=chunks, embedder=self.embedder)
            timer.stop("embedding_time_ms")

        self.timer = timer

    async def aindex_document(self, text: str, doc_id: str, metadata: dict) -> None:
        await asyncio.to_thread(self.index_document, text, doc_id, metadata)

    def index_document_with_pages(
        self,
        pages: List[Dict[str, Any]],
        doc_id: str,
        base_metadata: Dict[str, Any]
    ) -> None:
        """Index a document by chunking each page independently.

        Preserves page-level structure and metadata in chunks.

        P2.3: Chunking (text splitting) runs in parallel across pages, but all
        embedding calls are batched sequentially *after* chunking to avoid
        hammering the embedding API from multiple threads simultaneously.

        P3.4: Assigns ``chunk_index_global`` to each chunk so citation UI can
        reference chunks across the full document.

        Args:
            pages: List of dicts, each containing 'text' and 'metadata' keys.
            doc_id: Document identifier.
            base_metadata: Base metadata to include in all chunks.
        """
        import logging as _logging
        _logger = _logging.getLogger(__name__)
        import os

        timer = PipelineTimer()

        # Do not skip page-level indexing based on doc_id alone. Chunking config
        # changes must be allowed to create a fresh index; add_chunks performs
        # the safer content/config-hash dedupe after chunks are produced.
        is_indexed = False

        retriever_needs_index = False
        if hasattr(self.retriever, "index"):
            if hasattr(self.retriever, "chunks") and not self.retriever.chunks:
                retriever_needs_index = True
            elif hasattr(self.retriever, "sparse_retriever") and hasattr(self.retriever.sparse_retriever, "chunks") and not getattr(self.retriever.sparse_retriever, "chunks"):
                retriever_needs_index = True

        if is_indexed and not retriever_needs_index:
            return

        from concurrent.futures import ThreadPoolExecutor

        total_pages = len(pages)

        def _chunk_page_text_only(args: Tuple[int, Dict[str, Any]]) -> List[Chunk]:
            """Chunk a single page without embedding (P2.3: text-only pass)."""
            page_idx, page_dict = args
            page_text = page_dict.get("text", "")
            page_metadata = page_dict.get("metadata", {})

            if not page_text.strip():
                return []

            enriched_metadata = base_metadata.copy() if base_metadata else {}
            enriched_metadata["doc_id"] = doc_id
            enriched_metadata.update(page_metadata)
            enriched_metadata["chunker_fingerprint"] = _stable_config_fingerprint(self.chunker.get_config())
            enriched_metadata["content_hash"] = hashlib.sha256(
                f"{enriched_metadata['chunker_fingerprint']}:{page_text}".encode("utf-8")
            ).hexdigest()

            # P2.3: If the chunker supports a text-only mode (no embeddings), use it.
            # Fall back to the normal chunk() path for non-semantic chunkers.
            if hasattr(self.chunker, "chunk_text_only"):
                page_chunks = self.chunker.chunk_text_only(text=page_text, metadata=enriched_metadata)
            else:
                page_chunks = self.chunker.chunk(text=page_text, metadata=enriched_metadata)

            return page_chunks

        timer.start("chunking_time_ms")

        try:
            worker_limit = int(os.environ.get("MAX_CONCURRENT_CHUNKING_WORKERS", 3))
        except ValueError:
            worker_limit = 3

        max_workers = min(worker_limit, max(1, len(pages)))

        all_chunks: List[Chunk] = []
        # Parallelize text-only chunking over pages (no embedding calls here).
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for page_chunks in executor.map(_chunk_page_text_only, enumerate(pages)):
                all_chunks.extend(page_chunks)

        timer.stop("chunking_time_ms")

        if not all_chunks:
            return

        # P3.4: Assign a sequential global chunk index across all pages.
        for global_idx, chunk in enumerate(all_chunks):
            if chunk.metadata is None:
                chunk.metadata = {}
            chunk.metadata["chunk_index_global"] = global_idx
            # Legacy per-page index (kept for backward-compat)
            chunk.metadata.setdefault("chunk_index", global_idx)

        # Index all chunks into the sparse retriever (BM25) first.
        if hasattr(self.retriever, "index"):
            self.retriever.index(all_chunks)

        # P2.3: Embed ALL chunks in a single sequential pass — one API client,
        # one flow of batches, respecting MAX_EMBED_BATCH_SIZE (default 96).
        if not is_indexed:
            timer.start("embedding_time_ms")
            self.vectorstore.add_chunks(chunks=all_chunks, embedder=self.embedder)
            timer.stop("embedding_time_ms")

        self.timer = timer

        _logger.info(
            "Indexed document %s: %d pages, %d total chunks",
            doc_id,
            total_pages,
            len(all_chunks),
        )


    async def aindex_document_with_pages(
        self,
        pages: List[Dict[str, Any]],
        doc_id: str,
        base_metadata: Dict[str, Any]
    ) -> None:
        """Async version of index_document_with_pages."""
        await asyncio.to_thread(
            self.index_document_with_pages,
            pages,
            doc_id,
            base_metadata,
        )

    def index_pdf_images(self, pdf_content: Any, filename: str, doc_id: str, base_metadata: Dict[str, Any]) -> None:
        """Extract PDF images and index them in a sibling image vector collection.

        This is intentionally opt-in because the local CLIP model may download
        weights on first use. Enable with ``PDF_IMAGE_INDEXING_ENABLED=true``.
        """
        if os.getenv("PDF_IMAGE_INDEXING_ENABLED", "false").strip().lower() not in {"1", "true", "yes", "on"}:
            return

        collection_name = getattr(self.vectorstore, "collection_name", None)
        if not collection_name:
            logger.warning("Skipping image indexing because the vectorstore has no collection_name")
            return

        try:
            from app.services.embedding.clip_image_embedder import CLIPImageEmbedder
            from app.services.vectorstore.chroma_store import ChromaStore
            from app.utils.file_processor import FileProcessor

            image_store = ChromaStore(collection_name=f"{collection_name}_images")
            if hasattr(image_store, "is_document_indexed") and image_store.is_document_indexed(doc_id=doc_id):
                return

            image_chunks = FileProcessor.extract_pdf_images(pdf_content, filename)
            if not image_chunks:
                logger.info("No PDF images found for document %s", doc_id)
                return

            for global_idx, chunk in enumerate(image_chunks):
                chunk.metadata = dict(chunk.metadata or {})
                chunk.metadata.update(base_metadata or {})
                chunk.metadata["doc_id"] = doc_id
                chunk.metadata["chunk_index_global"] = global_idx
                chunk.metadata["chunk_index"] = global_idx
                chunk.metadata["image_collection_name"] = image_store.collection_name

            image_store.add_chunks(chunks=image_chunks, embedder=CLIPImageEmbedder())
            logger.info(
                "Indexed %d image chunk(s) for document %s into collection %s",
                len(image_chunks),
                doc_id,
                image_store.collection_name,
            )
        except Exception as exc:
            logger.warning("PDF image indexing failed for '%s': %s", filename, exc)

    async def aindex_pdf_images(
        self,
        pdf_content: Any,
        filename: str,
        doc_id: str,
        base_metadata: Dict[str, Any],
    ) -> None:
        await asyncio.to_thread(self.index_pdf_images, pdf_content, filename, doc_id, base_metadata)

    def retrieve(self, query: str, top_k: int = 5) -> List[Tuple[Chunk, float]]:
        """Retrieves chunks similar to the query.
        """
        requested_top_k = max(1, int(top_k))
        candidate_top_k = requested_top_k
        if self.reranker:
            candidate_top_k = max(
                requested_top_k,
                self.rerank_fetch_k,
                int(getattr(self.reranker, "max_candidates", requested_top_k)),
            )

        # Time the active vector retrieval separately
        self.timer.start("retrieval_time_ms")

        if self.retriever:
            results = self.retriever.search(query=query, top_k=candidate_top_k)
        else:
            results = self.vectorstore.search(
                query=query, embedder=self.embedder, top_k=candidate_top_k
            )

        self.timer.stop("retrieval_time_ms")

        if self.reranker:
            min_candidates_for_rerank = max(
                requested_top_k + 1,
                int(getattr(self.reranker, "min_candidates", os.getenv("RERANK_MIN_CANDIDATES", "8"))),
            )
            if len(results) < min_candidates_for_rerank:
                return results[:requested_top_k]
            self.timer.start("reranking_time_ms")
            results = self.reranker.rerank(query, results, requested_top_k)
            self.timer.stop("reranking_time_ms")
            return results

        return results[:requested_top_k]

    async def aretrieve(self, query: str, top_k: int = 5) -> List[Tuple[Chunk, float]]:
        return await asyncio.to_thread(self.retrieve, query, top_k)

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

    async def agenerate(self, query: str, chunks: List[Any], llm_client: Optional[GeminiClient] = None) -> str:
        target_llm = llm_client or self.llm_client
        if target_llm and hasattr(target_llm, "generate_async"):
            return await target_llm.generate_async(query=query, chunks=chunks, memory=self.memory)
        return await asyncio.to_thread(self.generate, query, chunks, llm_client)

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

    async def agenerate_stream(self, query: str, chunks: List[Any], llm_client: Optional[GeminiClient] = None):
        target_llm = llm_client or self.llm_client
        if not target_llm:
            yield "LLM Client not initialized."
            return

        if hasattr(target_llm, "generate_stream_async"):
            async for chunk_text in target_llm.generate_stream_async(query=query, chunks=chunks, memory=self.memory):
                yield chunk_text
            return

        # Fallback for synchronous generators: wrap the iterator itself properly.
        # We use a decorator or a helper to make it semi-async.
        def _get_iter():
            return self.generate_stream(query, chunks, llm_client)

        for chunk_text in await asyncio.to_thread(_get_iter):
            yield chunk_text
            await asyncio.sleep(0) # Yield control

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
