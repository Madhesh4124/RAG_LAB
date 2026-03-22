import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.chat import ChatMessage
from app.models.metrics import Metrics
from app.services.analysis import RetrievalAnalyzer

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

@router.get("/{message_id}")
def analyze_message(message_id: uuid.UUID, db: Session = Depends(get_db)):
    # 1. Fetch the message natively mapped
    msg = db.get(ChatMessage, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
        
    if msg.role != "assistant":
        raise HTTPException(status_code=400, detail="Analysis is logically only available for assistant messages")
        
    # 2. Fetch associated metrics (if any timer payloads caught mapped traces securely)
    stmt = select(Metrics).where(Metrics.message_id == message_id)
    metrics_record = db.execute(stmt).scalars().first()
    
    # 3. Parse retrieved chunks and instantly leverage our abstract Analyzer class seamlessly
    chunks_data = msg.retrieved_chunks or []
    analyzer = RetrievalAnalyzer(chunks_data)
    
    # Construct structured insight payload natively mapped
    return {
        "message_id": message_id,
        "total_chunks_retrieved": len(chunks_data),
        "avg_similarity": analyzer.get_avg_similarity(),
        "warning_flag": analyzer.has_low_confidence(),
        "top_contributors": analyzer.get_top_contributors(),
        "ranked_chunks": analyzer.get_ranked_chunks(),
        "timing_breakdown": {
            "chunking_time_ms": metrics_record.chunking_time_ms if metrics_record else None,
            "embedding_time_ms": metrics_record.embedding_time_ms if metrics_record else None,
            "retrieval_time_ms": metrics_record.retrieval_time_ms if metrics_record else None,
            "reranking_time_ms": metrics_record.reranking_time_ms if metrics_record else None,
            "llm_time_ms": metrics_record.llm_time_ms if metrics_record else None,
            "total_time_ms": metrics_record.total_time_ms if metrics_record else None,
        } if metrics_record else None
    }
