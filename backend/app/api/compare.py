import uuid
import os
from copy import deepcopy
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.rag_config import RAGConfig
from app.models.chat import ChatMessage
from app.models.metrics import Metrics
from app.services.pipeline_factory import PipelineFactory
from app.utils.timing import PipelineTimer

router = APIRouter(prefix="/api/compare", tags=["compare"])


@router.post("")
@router.post("/")
async def compare_configs(
    document_id: uuid.UUID = Body(...),
    query: str = Body(...),
    config_ids: Optional[List[uuid.UUID]] = Body(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Compare the same query across multiple RAG configurations.
    If config_ids not provided, returns all configs for the document.
    """
    doc_stmt = select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
    doc = (await db.execute(doc_stmt)).scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get configs to compare
    if config_ids:
        configs = []
        for cid in config_ids:
            cfg_stmt = select(RAGConfig).where(
                RAGConfig.id == cid,
                RAGConfig.user_id == current_user.id,
                RAGConfig.document_id == document_id,
            )
            cfg = (await db.execute(cfg_stmt)).scalars().first()
            if cfg:
                configs.append(cfg)
    else:
        # Get all configs for this document
        stmt = select(RAGConfig).where(
            RAGConfig.document_id == document_id,
            RAGConfig.user_id == current_user.id,
        )
        configs = (await db.execute(stmt)).scalars().all()
    
    if not configs:
        return {"results": [], "error": "No configurations found for this document"}

    max_configs = int(os.getenv("COMPARE_MAX_CONFIGS_PER_REQUEST", "2"))
    truncated = False
    if max_configs > 0 and len(configs) > max_configs:
        configs = configs[:max_configs]
        truncated = True
    
    results = []
    
    for config in configs:
        try:
            timer = PipelineTimer()
            retrieval_cfg = config.config_json.get("retriever", {}) if config.config_json else {}
            top_k = int(retrieval_cfg.get("top_k", 5))
            similarity_threshold = retrieval_cfg.get("similarity_threshold", None)
            
            # Build pipeline
            timer.start("chunking_time_ms")
            pipeline_config = deepcopy(config.config_json or {})
            vectorstore_cfg = deepcopy(pipeline_config.get("vectorstore", {}))
            if vectorstore_cfg.get("type") == "chroma":
                vectorstore_cfg["collection_name"] = f"user_{current_user.id}_rag_cfg_{config.id}"
                pipeline_config["vectorstore"] = vectorstore_cfg

            pipeline = PipelineFactory.create_pipeline(pipeline_config)
            
            # Index document
            metadata = {"filename": doc.filename, "file_type": doc.file_type}
            await pipeline.aindex_document(
                text=doc.content,
                doc_id=str(document_id),
                metadata=metadata
            )
            timer.stop("chunking_time_ms")
            
            # Retrieve chunks
            timer.start("retrieval_time_ms")
            retrieved_results = await pipeline.aretrieve(query, top_k=top_k)

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
                    answer = await pipeline.llm_client.generate_async(query, retrieved_chunks)
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

            timings = timer.to_metrics_dict() if hasattr(timer, "to_metrics_dict") else timer.get_timings()
            if retrieved_results and isinstance(retrieved_results[0], tuple):
                chunk_scores = [float(item[1]) for item in retrieved_results if isinstance(item, tuple) and len(item) == 2]
            else:
                chunk_scores = [float(getattr(chunk, "score", 0.0)) for chunk in retrieved_chunks]
            avg_similarity_for_db = (sum(chunk_scores) / len(chunk_scores)) if chunk_scores else 0.0

            assistant_msg = ChatMessage(
                user_id=current_user.id,
                document_id=document_id,
                config_id=config.id,
                role="assistant",
                content=answer,
                retrieved_chunks=[
                    {
                        "id": str(getattr(chunk, "id", idx)),
                        "text": getattr(chunk, "text", str(chunk)),
                        "score": float(chunk_scores[idx]) if idx < len(chunk_scores) else 0.0,
                    }
                    for idx, chunk in enumerate(retrieved_chunks)
                ],
            )
            db.add(assistant_msg)
            await db.flush()

            metrics_record = Metrics(
                message_id=assistant_msg.id,
                chunking_time_ms=timings["chunking_time_ms"],
                embedding_time_ms=timings.get("embedding_time_ms", 0),
                retrieval_time_ms=timings["retrieval_time_ms"],
                llm_time_ms=timings["llm_time_ms"],
                total_time_ms=timings["total_time_ms"],
                avg_similarity=avg_similarity_for_db,
                token_count=len(answer.split()),
            )
            db.add(metrics_record)
            await db.commit()

            result["message_id"] = str(assistant_msg.id)
            results.append(result)
            
        except Exception as e:
            await db.rollback()
            # Include error result for this config
            results.append({
                "configId": str(config.id),
                "configName": config.name,
                "error": f"Failed to run comparison: {str(e)}",
                "answer": "",
                "metrics": {"response_time_ms": 0, "chunks_retrieved": 0, "avg_similarity": 0, "token_count": 0},
                "chunks": []
            })
    
    response = {"results": results}
    if truncated:
        response["warning"] = (
            f"Compared first {max_configs} configs only to avoid provider rate limits. "
            "Set COMPARE_MAX_CONFIGS_PER_REQUEST to increase this limit."
        )
    return response
