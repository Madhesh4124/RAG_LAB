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
from app.database import get_db
from app.models.document import Document
from app.services.pipeline_manager import PipelineManager

router = APIRouter(prefix="/compare", tags=["compare"])


def _get_active_document_text(db: Session) -> str:
    for pipeline in reversed(list(PipelineManager._cache.values())):
        text = getattr(pipeline, "last_document_text", None)
        if text:
            return text

    stmt = select(Document).order_by(Document.upload_date.desc())
    document = db.execute(stmt).scalars().first()
    if document and document.content:
        return document.content

    raise HTTPException(
        status_code=400,
        detail="No active document found. Upload a document first.",
    )


@router.post("/index", response_model=IndexResponse)
async def compare_index(request: IndexRequest, db: Session = Depends(get_db)) -> IndexResponse:
    document_text = _get_active_document_text(db)
    return await index_config(request.config, document_text)


@router.post("/run", response_model=CompareResponse)
async def run_compare(request: CompareRequest) -> CompareResponse:
    if len(request.configs) < 1 or len(request.configs) > 4:
        raise HTTPException(status_code=422, detail="Between 1 and 4 configs required.")

    for config in request.configs:
        if not collection_exists(config.collection_name, config.embedding_model):
            raise HTTPException(
                status_code=422,
                detail=f"Config '{config.collection_name}' has not been indexed yet. Call /compare/index first.",
            )

    results = await run_comparison(query=request.query, configs=request.configs)
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
