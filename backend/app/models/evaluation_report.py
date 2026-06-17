import uuid
from datetime import datetime, timezone
from typing import Optional, Any, Dict

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Uuid

from app.database import Base


class EvaluationReport(Base):
    """Full evaluation report (retrieval metrics + answer quality + chunk judgments)."""

    __tablename__ = "evaluation_reports"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(Uuid(as_uuid=True), ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True, index=True)
    mode = Column(String(64), nullable=True)
    report_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EvaluationReportResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    message_id: Optional[uuid.UUID] = None
    mode: Optional[str] = None
    report_json: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationReportSummary(BaseModel):
    id: uuid.UUID
    message_id: Optional[uuid.UUID] = None
    mode: Optional[str] = None
    created_at: datetime
    # Top-level metrics extracted for quick display
    query: Optional[str] = None
    faithfulness: Optional[float] = None
    answer_relevancy: Optional[float] = None
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None
    precision_at_k: Optional[float] = None
    recall_at_k: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
