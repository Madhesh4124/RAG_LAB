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
    from app.services.pipeline_factory import PipelineFactory

    doc = db.get(Document, doc_id)
    config = db.get(RAGConfig, config_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    timer = PipelineTimer()
    
    try:
        pipeline = PipelineFactory.create_pipeline(config.config_json)
        retrieval_cfg = config.config_json.get("retriever", {}) if config.config_json else {}
        top_k = int(retrieval_cfg.get("top_k", 5))
        similarity_threshold = retrieval_cfg.get("similarity_threshold", None)

        timer.start("chunking_time_ms")
        pipeline.index_document(
            text=doc.content,
            doc_id=str(doc_id),
            metadata={"filename": doc.filename, "file_type": doc.file_type}
        )
        timer.stop("chunking_time_ms")

        timer.start("retrieval_time_ms")
        retrieved_results = pipeline.retrieve(query, top_k=top_k)

        if similarity_threshold is not None and retrieved_results and isinstance(retrieved_results[0], tuple):
            retrieved_results = [
                (chunk, score)
                for chunk, score in retrieved_results
                if score >= float(similarity_threshold)
            ]
        timer.stop("retrieval_time_ms")
        
        if retrieved_results and isinstance(retrieved_results[0], tuple):
            retrieved_chunks_only = [res[0] for res in retrieved_results]
        else:
            retrieved_chunks_only = retrieved_results
            
        timer.start("llm_time_ms")
        answer = pipeline.generate(query, retrieved_chunks_only)
        timer.stop("llm_time_ms")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    retrieved_chunks = []
    if 'retrieved_results' in locals():
        for i, res in enumerate(retrieved_results):
            if isinstance(res, tuple) and len(res) == 2:
                chunk, score = res
                retrieved_chunks.append({
                    "id": str(getattr(chunk, "id", i)), 
                    "text": getattr(chunk, "text", str(chunk)), 
                    "score": float(score)
                })
            else:
                chunk = res
                retrieved_chunks.append({
                    "id": str(getattr(chunk, "id", i)), 
                    "text": getattr(chunk, "text", str(chunk)), 
                    "score": float(getattr(chunk, "score", 0.0))
                })

    timings = timer.to_metrics_dict() if hasattr(timer, "to_metrics_dict") else timer.get_timings()

    user_msg = ChatMessage(
        document_id=doc_id,
        config_id=config_id,
        role="user",
        content=query,
        retrieved_chunks=None
    )
    db.add(user_msg)
    
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