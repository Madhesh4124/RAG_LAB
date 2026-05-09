"""Index PDF tables: extract, clean, chunk, embed, and store in vectorstore.

This is a thin orchestrator that uses `pdf_table_extractor` to obtain
`Chunk` objects and then persists them into the configured vectorstore
via the project's `PipelineFactory` components.
"""

from typing import List
import logging

from app.services.pdf_table_extractor import extract_tables_from_file
from app.services.pipeline_factory import PipelineFactory
from app.services.chunking.base import Chunk

logger = logging.getLogger(__name__)


def index_pdf_tables(
    file_path: str,
    collection_name: str = "tables_collection",
    chunk_level: str = "row",
    include_header: bool = True,
    context_rows: int = 0,
    embedding_provider: str = "nvidia",
    embedding_model: str = "nvidia/nv-embed-v1",
) -> int:
    """Extract tables from *file_path* and index into a Chroma collection.

    Returns the number of chunks indexed.
    """
    # Extract chunks from tables
    chunks: List[Chunk] = extract_tables_from_file(
        file_path=file_path,
        chunk_level=chunk_level,
        include_header=include_header,
        context_rows=context_rows,
    )

    if not chunks:
        logger.info("No table chunks extracted from %s", file_path)
        return 0

    # Build embedder and vectorstore using PipelineFactory
    embedder = PipelineFactory.create_embedder({"provider": embedding_provider, "model": embedding_model})
    vectorstore = PipelineFactory.create_vectorstore({"type": "chroma", "collection_name": collection_name})

    # Attach doc-level metadata if missing
    for c in chunks:
        if "doc_id" not in c.metadata:
            c.metadata.setdefault("doc_id", file_path)

    # Add chunks to vectorstore
    vectorstore.add_chunks(chunks, embedder)

    logger.info("Indexed %d table chunks from %s into collection %s", len(chunks), file_path, collection_name)
    return len(chunks)
