import uuid
from typing import Any, Dict, Optional
from sqlalchemy import Column, Integer, Text, ForeignKey, JSON, Uuid
from pydantic import BaseModel, ConfigDict
from app.database import Base

# --- SQLAlchemy Model ---

class ChunkModel(Base):
    __tablename__ = "chunks"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    document_id = Column(Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_num = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    metadata_json = Column(JSON, nullable=True)


# --- Pydantic Schemas ---

class ChunkResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    sequence_num: int
    text: str
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    metadata_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
