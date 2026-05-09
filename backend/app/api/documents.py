import os
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.document import Document, DocumentListItemResponse, DocumentResponse
from app.models.rag_config import RAGConfig
from app.utils.file_processor import FileProcessor
from app.services.indexing_jobs import IndexingJobStore

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("/list", response_model=List[DocumentListItemResponse])
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.upload_date.desc())
        .offset(skip)
        .limit(limit)
    )
    return (await db.execute(stmt)).scalars().all()


@router.get("/search", response_model=List[DocumentListItemResponse])
async def search_documents(
    query: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Document)
        .where(Document.user_id == current_user.id, Document.filename.ilike(f"%{query}%"))
        .order_by(Document.upload_date.desc())
        .limit(limit)
    )
    return (await db.execute(stmt)).scalars().all()

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    config: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # --- P1.1: HTTP-level body size guard ------------------------------------
    max_bytes = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50")) * 1024 * 1024
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"Request body exceeds the maximum allowed size of {limit_mb} MB.",
        )
    # -------------------------------------------------------------------------
    try:
        processed_data = await FileProcessor.process_upload(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # --- P3.2: Content-hash deduplication ------------------------------------
    sha256 = processed_data.get("content_sha256")
    if sha256:
        dup_stmt = select(Document).where(
            Document.user_id == current_user.id,
            Document.content_sha256 == sha256,
        )
        existing = (await db.execute(dup_stmt)).scalars().first()
        if existing:
            # Return the existing document — no re-upload, no re-index needed.
            return existing
    # -------------------------------------------------------------------------

    new_doc = Document(
        user_id=current_user.id,
        filename=processed_data["filename"],
        content=processed_data["content"],
        file_type=processed_data["file_type"],
        file_size=processed_data["file_size"],
        content_sha256=sha256,
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)
    return new_doc


@router.get("/index-status/{job_id}")
async def get_index_status(job_id: str, current_user: User = Depends(get_current_user)):
    """P2.1 — Poll the status of a background indexing job.

    Returns JSON with fields: job_id, status (pending|indexing|ready|failed),
    progress_pct (0-100), error (if failed).
    """
    job = IndexingJobStore.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Indexing job not found")
    return job.to_dict()


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    doc = (await db.execute(stmt)).scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.get("/{doc_id}/chunks")
async def preview_chunks(
    doc_id: uuid.UUID,
    config_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc_stmt = select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    doc = (await db.execute(doc_stmt)).scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not config_id:
        raise HTTPException(status_code=400, detail="config_id is required to preview chunks. Please complete the configuration wizard.")
        
    cfg_stmt = select(RAGConfig).where(
        RAGConfig.id == config_id,
        RAGConfig.user_id == current_user.id,
        RAGConfig.document_id == doc_id,
    )
    config = (await db.execute(cfg_stmt)).scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
        
    try:
        from app.services.pipeline_factory import PipelineFactory
        
        chunker_cfg = (config.config_json or {}).get("chunker", {})
        embedder_cfg = (config.config_json or {}).get("embedder", {})

        # For semantic chunking only, we need the embedder; skip it for everything else
        strategy = chunker_cfg.get("type", "fixed_size")
        if strategy == "semantic":
            embedder = PipelineFactory.create_embedder(embedder_cfg)
        else:
            embedder = None

        # Only create the chunker — no vectorstore, no LLM, no retriever
        chunker = PipelineFactory.create_chunker(chunker_cfg, embedder=embedder)

        metadata = {"filename": doc.filename, "file_type": doc.file_type}

        # PDF rows store base64-encoded binary in `content`; decode/extract text
        # before preview chunking to avoid showing raw PDF bytes.
        if (doc.file_type or "").lower() == "pdf":
            try:
                pages = FileProcessor.extract_pdf_pages(doc.content, doc.filename)
                chunks = []
                for page in pages:
                    page_text = (page.get("text") or "").strip()
                    if not page_text:
                        continue
                    page_metadata = metadata.copy()
                    page_metadata.update(page.get("metadata") or {})
                    chunks.extend(chunker.chunk(page_text, page_metadata))
            except Exception:
                # Fallback for malformed or legacy PDF rows.
                plain_text = FileProcessor.extract_pdf_text_fallback(doc.content, doc.filename)
                chunks = chunker.chunk(plain_text, metadata)
        else:
            chunks = chunker.chunk(doc.content, metadata)

        enriched_chunks = []
        for idx, chunk in enumerate(chunks):
            chunk_dict = chunk.__dict__.copy() if hasattr(chunk, "__dict__") else dict(chunk)
            if isinstance(chunk_dict.get("id"), uuid.UUID):
                chunk_dict["id"] = str(chunk_dict["id"])
            chunk_dict["sequence_num"] = idx

            if idx > 0:
                prev_end = chunks[idx - 1].end_char
                if chunk.start_char < prev_end:
                    chunk_dict["overlap_prev"] = prev_end - chunk.start_char

            if idx < len(chunks) - 1:
                next_start = chunks[idx + 1].start_char
                if chunk.end_char > next_start:
                    chunk_dict["overlap_next"] = chunk.end_char - next_start

            enriched_chunks.append(chunk_dict)

        return {"chunks": enriched_chunks}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to preview chunks: {str(e)}")

@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(doc_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    doc = (await db.execute(stmt)).scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.delete(doc)
    await db.commit()
    return None


@router.post("/{doc_id}/index-tables")
async def index_document_tables(
    doc_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Extract tables from a stored PDF document and index them into Chroma.

    Runs in background and returns a job_id for polling index status.
    """
    stmt = select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    doc = (await db.execute(stmt)).scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if (doc.file_type or "").lower() != "pdf":
        raise HTTPException(status_code=400, detail="Document is not a PDF")

    # Create indexing job
    job_id = IndexingJobStore.create(doc_id=str(doc_id), config_id=str(uuid.uuid4()))

    def _bg_index_tables(job_id_local: str, pdf_bytes: bytes, filename: str):
        try:
            import tempfile
            from app.services.table_indexer import index_pdf_tables

            IndexingJobStore.update(job_id_local, status="indexing", progress_pct=0)
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
                tmp.write(pdf_bytes)
                tmp.flush()
                count = index_pdf_tables(file_path=tmp.name)
            IndexingJobStore.update(job_id_local, status="ready", progress_pct=100)
        except Exception as exc:
            IndexingJobStore.update(job_id_local, status="failed", error=str(exc))

    # Snapshot bytes to avoid DB session usage in the background task
    pdf_bytes = doc.content if isinstance(doc.content, (bytes, bytearray)) else doc.content.encode("utf-8")
    background_tasks.add_task(_bg_index_tables, job_id, pdf_bytes, doc.filename)

    await db.commit()

    return {"status": "indexing", "job_id": job_id, "document_id": str(doc_id)}
