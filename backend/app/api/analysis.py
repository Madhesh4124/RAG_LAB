import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.chat import ChatMessage

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

@router.get("/{message_id}")
def analyze_message(message_id: uuid.UUID, db: Session = Depends(get_db)):
    msg = db.get(ChatMessage, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
        
    if msg.role != "assistant":
        raise HTTPException(status_code=400, detail="Analysis is only available for assistant messages")
        
    chunks = msg.retrieved_chunks or []
    
    # Sort by similarity score highest to lowest
    sorted_chunks = sorted(chunks, key=lambda c: c.get("score", 0.0), reverse=True)
    
    # Highest similarity score and warning flag
    highest_score = sorted_chunks[0].get("score", 0.0) if sorted_chunks else 0.0
    warning_flag = highest_score < 0.5
    
    # Assuming top 3 chunks contributed the most natively
    top_contributors = sorted_chunks[:3]
    
    # Estimate total tokens (1 token ~ 4 chars)
    total_tokens = sum(len(c.get("text", "")) // 4 for c in sorted_chunks)
    total_tokens += len(msg.content) // 4
    
    return {
        "message_id": message_id,
        "total_token_estimate": total_tokens,
        "warning_flag": warning_flag,
        "highest_score": highest_score,
        "retrieved_chunks": sorted_chunks,
        "top_contributors": top_contributors
    }
