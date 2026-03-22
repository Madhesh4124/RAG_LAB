import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.rag_config import RAGConfig, RAGConfigCreate, RAGConfigResponse
import tempfile
import os
from fastapi import File, UploadFile, Form, BackgroundTasks
from fastapi.responses import FileResponse
from app.utils.serialization import ConfigSerializer

router = APIRouter(prefix="/api/config", tags=["config"])

@router.post("/", response_model=RAGConfigResponse)
def create_config(config_in: RAGConfigCreate, db: Session = Depends(get_db)):
    new_config = RAGConfig(
        document_id=config_in.document_id,
        name=config_in.name,
        config_json=config_in.config_json,
        is_active=config_in.is_active
    )
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    return new_config

@router.get("/list", response_model=List[RAGConfigResponse])
def list_configs(doc_id: Optional[uuid.UUID] = Query(None), db: Session = Depends(get_db)):
    stmt = select(RAGConfig)
    if doc_id:
        stmt = stmt.where(RAGConfig.document_id == doc_id)
    return db.execute(stmt).scalars().all()

@router.get("/{config_id}", response_model=RAGConfigResponse)
def get_config(config_id: uuid.UUID, db: Session = Depends(get_db)):
    config_obj = db.get(RAGConfig, config_id)
    if not config_obj:
        raise HTTPException(status_code=404, detail="Config not found")
    return config_obj

@router.get("/{config_id}/export")
def export_config(config_id: uuid.UUID, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    config_obj = db.get(RAGConfig, config_id)
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
    db: Session = Depends(get_db)
):
    content = await file.read()
    try:
        json_str = content.decode("utf-8")
        config_dict = ConfigSerializer.import_from_json(json_str)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid UTF-8 JSON.")
        
    new_config = RAGConfig(
        document_id=document_id,
        name=name,
        config_json=config_dict,
        is_active=True
    )
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    
    return new_config
