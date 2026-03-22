import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.rag_config import RAGConfig, RAGConfigCreate, RAGConfigResponse

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
