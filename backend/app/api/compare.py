import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.document import Document
from app.models.rag_config import RAGConfig
from app.services.pipeline_factory import PipelineFactory
from app.utils.timing import PipelineTimer

router = APIRouter(prefix="/api/compare", tags=["compare"])


@router.post("/")
def compare_configs(
    document_id: uuid.UUID = Body(...),
    query: str = Body(...),
    config_ids: Optional[List[uuid.UUID]] = Body(None),
    db: Session = Depends(get_db)
):
    """
    Compare the same query across multiple RAG configurations.
    If config_ids not provided, returns all configs for the document.
    """
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get configs to compare
    if config_ids:
        configs = []
        for cid in config_ids:
            cfg = db.get(RAGConfig, cid)
            if cfg and cfg.document_id == document_id:
                configs.append(cfg)
    else:
        # Get all configs for this document
        stmt = select(RAGConfig).where(RAGConfig.document_id == document_id)
        configs = db.execute(stmt).scalars().all()
    
    if not configs:
        return {"results": [], "error": "No configurations found for this document"}
    
    results = []
    
    for config in configs:
        try:
            timer = PipelineTimer()
            retrieval_cfg = config.config_json.get("retriever", {}) if config.config_json else {}
            top_k = int(retrieval_cfg.get("top_k", 5))
            similarity_threshold = retrieval_cfg.get("similarity_threshold", None)
            
            # Build pipeline
            timer.start("chunking_time_ms")
            pipeline = PipelineFactory.create_pipeline(config.config_json)
            
            # Index document
            metadata = {"filename": doc.filename, "file_type": doc.file_type}
            pipeline.index_document(
                text=doc.content,
                doc_id=str(document_id),
                metadata=metadata
            )
            timer.stop("chunking_time_ms")
            
            # Retrieve chunks
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
                retrieved_chunks = [res[0] for res in retrieved_results]
            else:
                retrieved_chunks = retrieved_results or []
            
            # Generate answer
            timer.start("llm_time_ms")
            answer = ""
            if pipeline.llm_client and hasattr(pipeline.llm_client, 'llm') and pipeline.llm_client.llm:
                try:
                    answer = pipeline.llm_client.generate(query, retrieved_chunks)
                except Exception as e:
                    answer = f"LLM generation failed: {str(e)}"
            else:
                answer = f"Answer generated from {len(retrieved_chunks)} retrieved chunks (LLM unavailable)"
            timer.stop("llm_time_ms")
            
            # Calculate average similarity
            avg_similarity = 0.0
            if retrieved_results and isinstance(retrieved_results[0], tuple):
                similarities = [res[1] for res in retrieved_results if len(res) > 1]
                if similarities:
                    avg_similarity = sum(similarities) / len(similarities)
            
            # Create result entry
            result = {
                "configId": str(config.id),
                "configName": config.name,
                "params": {
                    "chunking": config.config_json.get("chunker", {}),
                    "embedding": config.config_json.get("embedder", {}),
                    "retrieval": config.config_json.get("retriever", {}),
                },
                "answer": answer,
                "metrics": {
                    "response_time_ms": int(timer.get_total_ms()),
                    "chunks_retrieved": len(retrieved_chunks),
                    "avg_similarity": round(avg_similarity, 2),
                    "token_count": len(answer.split()),  # rough estimate
                },
                "chunks": [
                    {
                        "id": str(chunk.id) if hasattr(chunk, 'id') else chunk.get('id', ''),
                        "text": chunk.text if hasattr(chunk, 'text') else chunk.get('text', ''),
                        "metadata": chunk.metadata if hasattr(chunk, 'metadata') else chunk.get('metadata', {}),
                    }
                    for chunk in retrieved_chunks[:3]  # Include first 3 chunks
                ],
            }
            results.append(result)
            
        except Exception as e:
            # Include error result for this config
            results.append({
                "configId": str(config.id),
                "configName": config.name,
                "error": f"Failed to run comparison: {str(e)}",
                "answer": "",
                "metrics": {"response_time_ms": 0, "chunks_retrieved": 0, "avg_similarity": 0, "token_count": 0},
                "chunks": []
            })
    
    return {"results": results}
