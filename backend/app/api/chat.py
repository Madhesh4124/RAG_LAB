import uuid
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.document import Document
from app.models.rag_config import RAGConfig
from app.models.chat import ChatMessage, ChatMessageResponse
from app.utils.timing import PipelineTimer

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/")
def chat_endpoint(
    query: str = Body(...),
    doc_id: uuid.UUID = Body(...),
    config_id: uuid.UUID = Body(...),
    db: Session = Depends(get_db)
):
    from app.services.pipeline import PipelineFactory

    doc = db.get(Document, doc_id)
    config = db.get(RAGConfig, config_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    timer = PipelineTimer()
    
    try:
        timer.start("pipeline_build")
        pipeline = PipelineFactory.build(config.config_json)
        timer.stop("pipeline_build")

        timer.start("retrieval")
        # Ensure your pipeline.retrieve evaluates strings against the active DB chunks (not handled here natively)
        retrieved_chunks_objs = pipeline.retrieve(query) 
        timer.stop("retrieval")
        
        timer.start("generation")
        answer = pipeline.generate(query, retrieved_chunks_objs)
        timer.stop("generation")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Parse chunk entities to store them safely as JSON
    retrieved_chunks = [
        {
            "id": str(getattr(c, "id", i)), 
            "text": getattr(c, "text", str(c)), 
            "score": getattr(c, "score", 0.0)
        } 
        for i, c in enumerate(retrieved_chunks_objs)
    ]

    timings = timer.get_timings()

    # Save user message
    user_msg = ChatMessage(
        document_id=doc_id,
        config_id=config_id,
        role="user",
        content=query,
        retrieved_chunks=None
    )
    db.add(user_msg)
    
    # Save assistant response
    assistant_msg = ChatMessage(
        document_id=doc_id,
        config_id=config_id,
        role="assistant",
        content=answer,
        retrieved_chunks=retrieved_chunks
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return {
        "answer": answer,
        "retrieved_chunks": retrieved_chunks,
        "timings": timings,
        "message_id": assistant_msg.id
    }

@router.get("/history/{doc_id}", response_model=list[ChatMessageResponse])
def get_chat_history(doc_id: uuid.UUID, db: Session = Depends(get_db)):
    stmt = select(ChatMessage).where(ChatMessage.document_id == doc_id).order_by(ChatMessage.timestamp)
    return db.execute(stmt).scalars().all()
