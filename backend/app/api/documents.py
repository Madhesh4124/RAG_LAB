import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.document import Document, DocumentResponse
from app.models.rag_config import RAGConfig
from app.utils.file_processor import FileProcessor

router = APIRouter(prefix="/api/documents", tags=["documents"])

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    config: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        processed_data = await FileProcessor.process_upload(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    new_doc = Document(
        filename=processed_data["filename"],
        content=processed_data["content"],
        file_type=processed_data["file_type"],
        file_size=processed_data["file_size"]
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    return new_doc

@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: uuid.UUID, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.get("/{doc_id}/chunks")
def preview_chunks(doc_id: uuid.UUID, config_id: Optional[uuid.UUID] = Query(None), db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not config_id:
        raise HTTPException(status_code=400, detail="config_id is required to preview chunks. Please complete the configuration wizard.")
        
    config = db.get(RAGConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
        
    try:
        from app.services.pipeline_factory import PipelineFactory
        pipeline = PipelineFactory.create_pipeline(config.config_json)
        
        # Assumption: the pipeline provides access to a built chunker
        if hasattr(pipeline, "chunker"):
            metadata = {"filename": doc.filename, "file_type": doc.file_type}
            chunks = pipeline.chunker.chunk(doc.content, metadata)
            
            # Enrich chunks with sequence numbers and overlap info for frontend
            enriched_chunks = []
            for idx, chunk in enumerate(chunks):
                chunk_dict = chunk.__dict__.copy() if hasattr(chunk, "__dict__") else dict(chunk)
                # Convert UUID to string for JSON serialization
                if isinstance(chunk_dict.get("id"), uuid.UUID):
                    chunk_dict["id"] = str(chunk_dict["id"])
                chunk_dict["sequence_num"] = idx
                
                # Calculate overlap with previous chunk
                if idx > 0:
                    prev_end = chunks[idx - 1].end_char
                    if chunk.start_char < prev_end:
                        chunk_dict["overlap_prev"] = prev_end - chunk.start_char
                
                # Calculate overlap with next chunk
                if idx < len(chunks) - 1:
                    next_start = chunks[idx + 1].start_char
                    if chunk.end_char > next_start:
                        chunk_dict["overlap_next"] = chunk.end_char - next_start
                
                enriched_chunks.append(chunk_dict)
            
            return {"chunks": enriched_chunks}
        else:
            return {"chunks": [], "error": "Pipeline missing chunker component."}
    except Exception as e:
        return {"chunks": [], "error": f"Failed to preview chunks: {str(e)}"}

@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: uuid.UUID, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()
    return None
