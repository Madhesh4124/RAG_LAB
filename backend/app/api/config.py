import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.rag_config import RAGConfig, RAGConfigCreate, RAGConfigResponse
import tempfile
import os
from fastapi import File, UploadFile, Form, BackgroundTasks
from fastapi.responses import FileResponse
from app.utils.serialization import ConfigSerializer
from app.auth import get_current_user
from app.models.user import User
from app.models.document import Document
from app.services.best_preset import BEST_PRESET_NAME, BEST_PRESET_VERSION, get_best_preset_config
from pydantic import BaseModel

router = APIRouter(prefix="/api/config", tags=["config"])


class ApplyBestPresetRequest(BaseModel):
    document_id: uuid.UUID
    name: Optional[str] = None


@router.get("/best-preset")
async def get_best_preset(current_user: User = Depends(get_current_user)):
    _ = current_user  # keeps endpoint protected and future-proof for role-scoped presets
    return {
        "name": BEST_PRESET_NAME,
        "version": BEST_PRESET_VERSION,
        "config_json": get_best_preset_config(),
    }


@router.post("/best-preset/apply", response_model=RAGConfigResponse)
async def apply_best_preset(
    payload: ApplyBestPresetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc_stmt = select(Document).where(Document.id == payload.document_id, Document.user_id == current_user.id)
    owned_doc = (await db.execute(doc_stmt)).scalars().first()
    if not owned_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    config_name = payload.name or f"{BEST_PRESET_NAME} {BEST_PRESET_VERSION}"
    new_config = RAGConfig(
        user_id=current_user.id,
        document_id=payload.document_id,
        name=config_name,
        config_json=get_best_preset_config(),
        is_active=True,
    )
    db.add(new_config)
    await db.commit()
    await db.refresh(new_config)
    return new_config

@router.post("/", response_model=RAGConfigResponse)
async def create_config(
    config_in: RAGConfigCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc_stmt = select(Document).where(Document.id == config_in.document_id, Document.user_id == current_user.id)
    owned_doc = (await db.execute(doc_stmt)).scalars().first()
    if not owned_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    new_config = RAGConfig(
        user_id=current_user.id,
        document_id=config_in.document_id,
        name=config_in.name,
        config_json=config_in.config_json,
        is_active=config_in.is_active
    )
    db.add(new_config)
    await db.commit()
    await db.refresh(new_config)
    return new_config

@router.get("/list", response_model=List[RAGConfigResponse])
async def list_configs(
    doc_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RAGConfig).where(RAGConfig.user_id == current_user.id)
    if doc_id:
        stmt = stmt.where(RAGConfig.document_id == doc_id)
    return (await db.execute(stmt)).scalars().all()

@router.get("/{config_id}", response_model=RAGConfigResponse)
async def get_config(config_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(RAGConfig).where(RAGConfig.id == config_id, RAGConfig.user_id == current_user.id)
    config_obj = (await db.execute(stmt)).scalars().first()
    if not config_obj:
        raise HTTPException(status_code=404, detail="Config not found")
    return config_obj

@router.get("/{config_id}/export")
async def export_config(
    config_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RAGConfig).where(RAGConfig.id == config_id, RAGConfig.user_id == current_user.id)
    config_obj = (await db.execute(stmt)).scalars().first()
    if not config_obj:
        raise HTTPException(status_code=404, detail="Config not found")
        
    json_str = ConfigSerializer.export_to_json(config_obj)
    
    # Write to a temporary file to return as FileResponse
    fd, tmp_path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json_str)
        
    # Clean up the temp file after sending
    background_tasks.add_task(os.remove, tmp_path)
    
    return FileResponse(
        path=tmp_path,
        media_type="application/json",
        filename=f"rag_config_{config_id}.json"
    )

@router.post("/import", response_model=RAGConfigResponse)
async def import_config(
    document_id: uuid.UUID = Form(...),
    name: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    doc_stmt = select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
    owned_doc = (await db.execute(doc_stmt)).scalars().first()
    if not owned_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    content = await file.read()
    try:
        json_str = content.decode("utf-8")
        config_dict = ConfigSerializer.import_from_json(json_str)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid UTF-8 JSON.")
        
    new_config = RAGConfig(
        user_id=current_user.id,
        document_id=document_id,
        name=name,
        config_json=config_dict,
        is_active=True
    )
    db.add(new_config)
    await db.commit()
    await db.refresh(new_config)
    
    return new_config
