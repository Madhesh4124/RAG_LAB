import uuid
from typing import Any, Dict
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON, Uuid
from pydantic import BaseModel, ConfigDict
from app.database import Base

# --- SQLAlchemy Model ---

class RAGConfig(Base):
    __tablename__ = "rag_configs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    config_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)


# --- Pydantic Schemas ---

class RAGConfigCreate(BaseModel):
    document_id: uuid.UUID
    name: str
    config_json: Dict[str, Any]
    is_active: bool = True

class RAGConfigResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    document_id: uuid.UUID
    name: str
    config_json: Dict[str, Any]
    created_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
