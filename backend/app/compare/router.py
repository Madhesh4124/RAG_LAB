import asyncio
import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.compare.collection_registry import collection_exists, clear_compare_chroma_store
from app.compare.compare_runner import run_comparison
from app.compare.indexer import index_config
from app.compare.schemas import CompareRequest, CompareResponse, IndexRequest, IndexResponse
from app.auth import get_current_user
from app.database import get_db
from app.models.document import Document
from app.models.user import User
from app.services.pipeline_manager import PipelineManager

router = APIRouter(prefix="/compare", tags=["compare"])


def _get_active_document_text(db: Session, current_user: User, document_id=None) -> str:
    if document_id is not None:
        selected_stmt = select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
        selected_document = db.execute(selected_stmt).scalars().first()
        if not selected_document or not selected_document.content:
            raise HTTPException(status_code=404, detail="Selected document not found")
        return selected_document.content

    for pipeline in reversed(list(PipelineManager._cache.values())):
        text = getattr(pipeline, "last_document_text", None)
        if text:
            return text

    stmt = (
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.upload_date.desc())
    )
    document = db.execute(stmt).scalars().first()
    if document and document.content:
        return document.content

    raise HTTPException(
        status_code=400,
        detail="No active document found. Upload a document first.",
    )


@router.post("/index", response_model=IndexResponse)
async def compare_index(
    request: IndexRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IndexResponse:
    document_text = _get_active_document_text(db, current_user, document_id=request.document_id)
    return await index_config(request.config, document_text, user_scope=str(current_user.id))


@router.post("/run", response_model=CompareResponse)
async def run_compare(request: CompareRequest, current_user: User = Depends(get_current_user)) -> CompareResponse:
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

    results = await run_comparison(query=request.query, configs=request.configs, user_scope=str(current_user.id))
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
