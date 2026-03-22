import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, ForeignKey, JSON, DateTime, Uuid
from pydantic import BaseModel, ConfigDict
from app.database import Base

# --- SQLAlchemy Model ---

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    document_id = Column(Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    config_id = Column(Uuid(as_uuid=True), ForeignKey("rag_configs.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    retrieved_chunks = Column(JSON, nullable=True)


# --- Pydantic Schemas ---

class ChatMessageCreate(BaseModel):
    document_id: uuid.UUID
    config_id: uuid.UUID
    role: str
    content: str
    retrieved_chunks: Optional[List[Dict[str, Any]]] = None

class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    config_id: uuid.UUID
    role: str
    content: str
    timestamp: datetime
    retrieved_chunks: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(from_attributes=True)
