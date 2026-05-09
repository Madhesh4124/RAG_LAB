import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, String, Text, Integer, DateTime, Uuid, ForeignKey
from pydantic import BaseModel, ConfigDict
from app.database import Base

# --- SQLAlchemy Model ---

class Document(Base):
    __tablename__ = "documents"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    file_type = Column(String(50), nullable=False)
    upload_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    file_size = Column(Integer, nullable=False)
    # P3.2: SHA-256 of raw file bytes for content-level deduplication.
    # Nullable for backward-compatibility with rows uploaded before this column was added.
    content_sha256 = Column(String(64), nullable=True, index=True)


# --- Pydantic Schemas ---

class DocumentCreate(BaseModel):
    filename: str
    content: str
    file_type: str
    file_size: int

class DocumentResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    filename: str
    content: str
    file_type: str
    upload_date: datetime
    file_size: int
    content_sha256: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentListItemResponse(BaseModel):
    id: uuid.UUID
    filename: str
    file_type: str
    upload_date: datetime
    file_size: int

    model_config = ConfigDict(from_attributes=True)
