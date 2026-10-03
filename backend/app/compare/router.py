import asyncio
import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compare.collection_registry import collection_exists, clear_compare_chroma_store
from app.compare.compare_runner import run_comparison
from app.compare.indexer import index_config
from app.compare.schemas import CompareRequest, CompareResponse, IndexRequest, IndexResponse
from app.auth import get_current_user
from app.database import get_db
from app.models.document import Document
from app.models.user import User

router = APIRouter(prefix="/compare", tags=["compare"])


import logging
from app.utils.file_processor import FileProcessor

logger = logging.getLogger(__name__)


async def _get_active_document(db: AsyncSession, current_user: User, document_id=None) -> Document:
    if document_id is not None:
        selected_stmt = select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
        selected_document = (await db.execute(selected_stmt)).scalars().first()
        if not selected_document or not selected_document.content:
            raise HTTPException(status_code=404, detail="Selected document not found")
        return selected_document

    stmt = (
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.upload_date.desc())
    )
    document = (await db.execute(stmt)).scalars().first()
    if document and document.content:
        return document

    raise HTTPException(
        status_code=400,
        detail="No active document found. Upload a document first.",
    )


def _extract_document_data(doc: Document) -> tuple[str, list[dict], dict]:
    metadata = {"filename": doc.filename, "file_type": doc.file_type}
    is_pdf = (
        (doc.file_type and doc.file_type.lower() == "pdf")
        or (doc.filename and doc.filename.lower().endswith(".pdf"))
        or str(doc.content or "").startswith("pdf://")
    )
    if is_pdf:
        pages: list[dict] = []
        try:
            pages = FileProcessor.extract_pdf_pages(doc.content, doc.filename)
            text_parts = [p.get("text", "") for p in pages if p.get("text")]
            full_text = "\n\n".join(text_parts).strip()
            if full_text:
                return full_text, pages, metadata
        except Exception as exc:
            logger.warning("Compare: PDF page extraction failed for '%s': %s", doc.filename, exc)

        fallback = FileProcessor.extract_pdf_text_fallback(doc.content, doc.filename)
        return fallback, pages, metadata

    return str(doc.content or ""), [], metadata


@router.post("/index", response_model=IndexResponse)
async def compare_index(
    request: IndexRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IndexResponse:
    if request.document_ids and len(request.document_ids) > 0:
        docs_stmt = (
            select(Document)
            .where(Document.id.in_(request.document_ids), Document.user_id == current_user.id)
        )
        docs = (await db.execute(docs_stmt)).scalars().all()
        if not docs:
            raise HTTPException(status_code=404, detail="Selected documents not found")
        all_texts = []
        all_pages = []
        for d in docs:
            t, p, _ = _extract_document_data(d)
            if t:
                all_texts.append(f"--- Document: {d.filename} ---\n" + t)
            if p:
                all_pages.extend(p)
        doc_text = "\n\n".join(all_texts).strip()
        doc_pages = all_pages
        doc_meta = {"filenames": [d.filename for d in docs]}
    else:
        doc = await _get_active_document(db, current_user, document_id=request.document_id)
        doc_text, doc_pages, doc_meta = _extract_document_data(doc)

    return await index_config(
        request.config,
        doc_text,
        user_scope=str(current_user.id),
        document_pages=doc_pages,
        doc_metadata=doc_meta,
    )


@router.post("/run", response_model=CompareResponse)
async def run_compare(
    request: CompareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompareResponse:
    if len(request.configs) < 1 or len(request.configs) > 4:
        raise HTTPException(status_code=422, detail="Between 1 and 4 configs required.")

    for config in request.configs:
        if not collection_exists(
            config.collection_name,
            config.embedding_provider,
            config.embedding_model,
            user_scope=str(current_user.id),
        ):
            raise HTTPException(
                status_code=422,
                detail=f"Config '{config.collection_name}' has not been indexed yet. Call /compare/index first.",
            )

    results = await run_comparison(query=request.query, configs=request.configs, user_scope=str(current_user.id), db=db)
    await db.commit()
    return CompareResponse(query=request.query, results=results)


@router.post("/clear-chromadb")
async def clear_chromadb() -> dict:
    """Clear all local Chroma persistence used by the app."""
    clear_compare_chroma_store()

    app_root = Path(__file__).resolve().parents[2]
    extra_dirs = [
        app_root / "chroma_db",
        Path(os.getenv("CHROMA_PERSIST_DIR", str(app_root / "chroma_db"))),
    ]

    cleared = []
    for directory in extra_dirs:
        try:
            if directory.exists():
                shutil.rmtree(directory, ignore_errors=True)
            directory.mkdir(parents=True, exist_ok=True)
            cleared.append(str(directory))
        except Exception:
            continue

    return {"status": "success", "cleared": cleared}
