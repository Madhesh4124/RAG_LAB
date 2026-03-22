import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import Column, Float, Integer, ForeignKey, DateTime, Uuid
from pydantic import BaseModel, ConfigDict
from app.database import Base

# --- SQLAlchemy Model ---

class Metrics(Base):
    __tablename__ = "metrics"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    message_id = Column(Uuid(as_uuid=True), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    chunking_time_ms = Column(Float, nullable=False, default=0.0)
    embedding_time_ms = Column(Float, nullable=False, default=0.0)
    retrieval_time_ms = Column(Float, nullable=False, default=0.0)
    reranking_time_ms = Column(Float, nullable=True)
    llm_time_ms = Column(Float, nullable=False, default=0.0)
    total_time_ms = Column(Float, nullable=False, default=0.0)
    token_count = Column(Integer, nullable=True)
    avg_similarity = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# --- Pydantic Schemas ---

class MetricsResponse(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID
    chunking_time_ms: float
    embedding_time_ms: float
    retrieval_time_ms: float
    reranking_time_ms: Optional[float] = None
    llm_time_ms: float
    total_time_ms: float
    token_count: Optional[int] = None
    avg_similarity: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
