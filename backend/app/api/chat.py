import uuid
import asyncio
from copy import deepcopy
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import AsyncSessionLocal, get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.rag_config import RAGConfig
from app.models.chat import ChatMessage, ChatMessageResponse
from app.models.metrics import Metrics
from app.utils.timing import PipelineTimer
from app.services.rate_limiter import DatabaseRateLimiter, get_rate_limiter

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _normalize_scores_for_display(scores: List[float]) -> List[float]:
    """Normalize retrieval/rerank scores to a stable [0, 1] range for UI display."""
    if not scores:
        return []

    cleaned = [float(s) for s in scores]
    rate_limiter: DatabaseRateLimiter = Depends(get_rate_limiter),
    db: AsyncSession = Depends(get_db),
    if all(abs(s) < 1e-12 for s in cleaned):
        n = len(cleaned)
        if n == 1:
            return [1.0]
        return [max(0.0, (n - idx) / n) for idx in range(n)]

    # If already in [0, 1], keep as-is.
    if all(0.0 <= s <= 1.0 for s in cleaned):
        return cleaned

    # Fallback for logits or arbitrary scales.
    mn = min(cleaned)
    mx = max(cleaned)
    if abs(mx - mn) < 1e-12:
        return [0.5 for _ in cleaned]
    return [(s - mn) / (mx - mn) for s in cleaned]


def _fallback_answer_from_chunks(query: str, chunks: List[Any]) -> str:
    """Build a deterministic answer from retrieved chunks when LLM is unavailable."""
    if not chunks:
        return "No relevant chunks were retrieved for this question."

    excerpts = []
    for idx, chunk in enumerate(chunks[:3], start=1):
        text = str(getattr(chunk, "text", chunk)).strip().replace("\n", " ")
        if len(text) > 240:
            text = text[:240] + "..."
        excerpts.append(f"{idx}. {text}")

    joined = "\n".join(excerpts)
    return (
        "LLM is temporarily unavailable, so this answer is based directly on retrieved chunks.\n"
        f"Question: {query}\n"
        "Relevant excerpts:\n"
        f"{joined}"
    )


class PrepareChatRequest(BaseModel):
    document_id: uuid.UUID
    document_ids: List[uuid.UUID] | None = None
    config_id: uuid.UUID


@router.post("/prepare")
async def prepare_chat_session(
    payload: PrepareChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.pipeline_manager import PipelineManager

    target_doc_ids = payload.document_ids or [payload.document_id]
    normalized_doc_ids = []
    seen = set()
    for item in target_doc_ids:
        key = str(item)
        if key not in seen:
            seen.add(key)
            normalized_doc_ids.append(item)

    doc_stmt = select(Document).where(Document.id.in_(normalized_doc_ids), Document.user_id == current_user.id)
    cfg_stmt = select(RAGConfig).where(
        RAGConfig.id == payload.config_id,
        RAGConfig.user_id == current_user.id,
        RAGConfig.document_id == payload.document_id,
    )

    docs = (await db.execute(doc_stmt)).scalars().all()
    config = (await db.execute(cfg_stmt)).scalars().first()

    if not docs or len(docs) != len(normalized_doc_ids):
        raise HTTPException(status_code=404, detail="Document not found")
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    pipeline_config = deepcopy(config.config_json or {})
    vectorstore_cfg = deepcopy(pipeline_config.get("vectorstore", {}))
    if vectorstore_cfg.get("type") == "chroma":
        vectorstore_cfg["collection_name"] = f"user_{current_user.id}_rag_cfg_{config.id}"
        pipeline_config["vectorstore"] = vectorstore_cfg

    pipeline = PipelineManager.get_pipeline(f"{current_user.id}:{config.id}", pipeline_config)
    for doc in docs:
        await pipeline.aindex_document(
            text=doc.content,
            doc_id=str(doc.id),
            metadata={"filename": doc.filename, "file_type": doc.file_type},
        )

    return {
        "status": "ready",
        "document_id": str(payload.document_id),
        "document_ids": [str(item) for item in normalized_doc_ids],
        "config_id": str(payload.config_id),
    }

@router.post("/")
async def chat_endpoint(
    query: str = Body(...),
    doc_id: uuid.UUID = Body(...),
    config_id: uuid.UUID = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rate_limiter: DatabaseRateLimiter = Depends(get_rate_limiter),
):
    from app.api.evaluation import score_message
    from app.services.pipeline_manager import PipelineManager
    
    # Check rate limit for LLM calls
    scope_key = rate_limiter.build_scope_key(user_id=current_user.id)
    allowed, remaining, error_msg = await rate_limiter.check_rate_limit(scope_key, "llm")
    if not allowed:
        raise HTTPException(status_code=429, detail=error_msg)

    doc_stmt = select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    cfg_stmt = select(RAGConfig).where(
        RAGConfig.id == config_id,
        RAGConfig.user_id == current_user.id,
        RAGConfig.document_id == doc_id,
    )
    doc = (await db.execute(doc_stmt)).scalars().first()
    config = (await db.execute(cfg_stmt)).scalars().first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    timer = PipelineTimer()
    
    try:
        pipeline_config = deepcopy(config.config_json or {})
        vectorstore_cfg = deepcopy(pipeline_config.get("vectorstore", {}))
        if vectorstore_cfg.get("type") == "chroma":
            vectorstore_cfg["collection_name"] = f"user_{current_user.id}_rag_cfg_{config.id}"
            pipeline_config["vectorstore"] = vectorstore_cfg

        pipeline = PipelineManager.get_pipeline(f"{current_user.id}:{config_id}", pipeline_config)
        retrieval_cfg = config.config_json.get("retriever", {}) if config.config_json else {}
        top_k = int(retrieval_cfg.get("top_k", 5))
        similarity_threshold = retrieval_cfg.get("similarity_threshold", None)

        timer.start("chunking_time_ms")
        await pipeline.aindex_document(
            text=doc.content,
            doc_id=str(doc_id),
            metadata={"filename": doc.filename, "file_type": doc.file_type}
        )
        timer.stop("chunking_time_ms")

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
            retrieved_chunks_only = [res[0] for res in retrieved_results]
        else:
            retrieved_chunks_only = retrieved_results
            
        timer.start("llm_time_ms")
        try:
            answer = await pipeline.agenerate(query, retrieved_chunks_only)
            # Record successful LLM call
            await rate_limiter.record_call(scope_key, "llm", current_user.id)
        except Exception:
            answer = _fallback_answer_from_chunks(query, retrieved_chunks_only)
        finally:
            timer.stop("llm_time_ms")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    retrieved_chunks = []
    if 'retrieved_results' in locals():
        raw_scores = []
        for res in retrieved_results:
            if isinstance(res, tuple) and len(res) == 2:
                raw_scores.append(float(res[1]))
            else:
                raw_scores.append(float(getattr(res, "score", 0.0)))

        display_scores = _normalize_scores_for_display(raw_scores)

        for i, res in enumerate(retrieved_results):
            if isinstance(res, tuple) and len(res) == 2:
                chunk, score = res
                retrieved_chunks.append({
                    "id": str(getattr(chunk, "id", i)), 
                    "text": getattr(chunk, "text", str(chunk)), 
                    "score": float(display_scores[i]) if i < len(display_scores) else float(score)
                })
            else:
                chunk = res
                retrieved_chunks.append({
                    "id": str(getattr(chunk, "id", i)), 
                    "text": getattr(chunk, "text", str(chunk)), 
                    "score": float(display_scores[i]) if i < len(display_scores) else float(getattr(chunk, "score", 0.0))
                })

    user_msg = ChatMessage(
        user_id=current_user.id,
        document_id=doc_id,
        config_id=config_id,
        role="user",
        content=query,
        retrieved_chunks=None
    )
    db.add(user_msg)
    
    assistant_msg = ChatMessage(
        user_id=current_user.id,
        document_id=doc_id,
        config_id=config_id,
        role="assistant",
        content=answer,
        retrieved_chunks=retrieved_chunks
    )
    db.add(assistant_msg)

    timings = timer.to_metrics_dict() if hasattr(timer, "to_metrics_dict") else timer.get_timings()
    response_timings = {k: round(float(v), 0) for k, v in timings.items()}
    chunk_scores = [float(chunk.get("score", 0.0)) for chunk in retrieved_chunks]
    avg_similarity = (sum(chunk_scores) / len(chunk_scores)) if chunk_scores else 0.0

    await db.flush()
    metrics_record = Metrics(
        message_id=assistant_msg.id,
        chunking_time_ms=timings["chunking_time_ms"],
        embedding_time_ms=timings.get("embedding_time_ms", 0),
        retrieval_time_ms=timings["retrieval_time_ms"],
        llm_time_ms=timings["llm_time_ms"],
        total_time_ms=timings["total_time_ms"],
        avg_similarity=avg_similarity,
        token_count=len(answer.split()),
    )
    db.add(metrics_record)

    llm_client = getattr(pipeline, "llm_client", None)
    try:
        score_message(
            db=db,
            assistant_msg=assistant_msg,
            query_text=query,
            llm_client=llm_client,
            chunks=retrieved_chunks_only,
        )
    except Exception:
        # Evaluation should not block normal chat responses.
        pass

    await db.commit()
    await db.refresh(assistant_msg)

    return {
        "answer": answer,
        "retrieved_chunks": retrieved_chunks,
        "timings": response_timings,
        "message_id": assistant_msg.id
    }

from fastapi.responses import StreamingResponse
import json

@router.post("/stream")
async def chat_stream_endpoint(
    query: str = Body(...),
    doc_id: uuid.UUID = Body(...),
    doc_ids: List[uuid.UUID] | None = Body(None),
    config_id: uuid.UUID = Body(...),
    current_user: User = Depends(get_current_user),
):
    """Streaming version for better perceived latency."""
    from app.services.pipeline_manager import PipelineManager
    # Check rate limit for LLM calls using a short-lived DB session.
    scope_key = f"user:{current_user.id}"
    async with AsyncSessionLocal() as limiter_db:
        limiter = DatabaseRateLimiter(limiter_db)
        allowed, remaining, error_msg = await limiter.check_rate_limit(scope_key, "llm")
        if not allowed:
            raise HTTPException(status_code=429, detail=error_msg)

    requested_ids = doc_ids or [doc_id]
    normalized_ids = []
    seen = set()
    for item in requested_ids:
        key = str(item)
        if key not in seen:
            seen.add(key)
            normalized_ids.append(item)

    doc_stmt = select(Document).where(Document.id.in_(normalized_ids), Document.user_id == current_user.id)
    cfg_stmt = select(RAGConfig).where(
        RAGConfig.id == config_id,
        RAGConfig.user_id == current_user.id,
        RAGConfig.document_id == doc_id,
    )
    async with AsyncSessionLocal() as read_db:
        docs = (await read_db.execute(doc_stmt)).scalars().all()
        config = (await read_db.execute(cfg_stmt)).scalars().first()
    
    if not docs or len(docs) != len(normalized_ids) or not config:
        raise HTTPException(status_code=404, detail="Resource not found")

    pipeline_config = deepcopy(config.config_json or {})
    if pipeline_config.get("vectorstore", {}).get("type") == "chroma":
        pipeline_config["vectorstore"]["collection_name"] = f"user_{current_user.id}_rag_cfg_{config_id}"

    pipeline = PipelineManager.get_pipeline(f"{current_user.id}:{config_id}", pipeline_config)
    retrieval_cfg = pipeline_config.get("retriever", {})
    top_k = int(retrieval_cfg.get("top_k", 5))
    similarity_threshold = float(retrieval_cfg.get("similarity_threshold", 0.0))

    async def event_generator():
        try:
            # 1. Notify immediately; start indexing inside generator so response begins right away
            yield f"data: {json.dumps({'type': 'status', 'message': f'Indexing {len(docs)} document(s)…'})}\n\n"

            for doc in docs:
                await pipeline.aindex_document(doc.content, str(doc.id), {"filename": doc.filename, "file_type": doc.file_type})

            _msg2 = json.dumps({'type': 'status', 'message': 'Retrieving relevant chunks…'})
            yield f"data: {_msg2}\n\n"
            results = await pipeline.aretrieve(query, top_k=top_k)

            if similarity_threshold > 0 and results and isinstance(results[0], tuple):
                filtered = [(c, s) for c, s in results if s >= similarity_threshold]
                # Safety: never filter out everything — fall back to unfiltered top results
                results = filtered if filtered else results

            chunks = [res[0] if isinstance(res, tuple) else res for res in results]
            raw_scores = [float(res[1]) if isinstance(res, tuple) else float(getattr(res, "score", 0.0)) for res in results]
            scores = _normalize_scores_for_display(raw_scores)

            # 2. Send full chunk text + score
            chunk_meta = [
                {"text": getattr(c, "text", ""), "score": round(scores[idx], 4)}
                for idx, c in enumerate(chunks)
            ]
            yield f"data: {json.dumps({'type': 'metadata', 'chunks': chunk_meta})}\n\n"

            # 3. Stream generation tokens
            full_response = ""
            async for token in pipeline.agenerate_stream(query, chunks):
                full_response += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            # Record successful LLM call in a short-lived session.
            async with AsyncSessionLocal() as limiter_db:
                limiter = DatabaseRateLimiter(limiter_db)
                await limiter.record_call(scope_key, "llm", current_user.id)

            # Notify UI immediately that generation is complete.
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

            # 4. Persist to DB (non-blocking for UI because done is already sent)
            try:
                async with AsyncSessionLocal() as write_db:
                    user_msg = ChatMessage(
                        user_id=current_user.id,
                        document_id=doc_id,
                        config_id=config_id,
                        role="user",
                        content=query,
                    )
                    write_db.add(user_msg)
                    assistant_msg = ChatMessage(
                        user_id=current_user.id,
                        document_id=doc_id,
                        config_id=config_id,
                        role="assistant",
                        content=full_response,
                        retrieved_chunks=[{"text": getattr(c, "text", ""), "score": scores[i]} for i, c in enumerate(chunks)]
                    )
                    write_db.add(assistant_msg)
                    await write_db.commit()
            except Exception:
                pass

        except asyncio.CancelledError:
            # Client disconnected mid-stream.
            raise

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/history/{doc_id}", response_model=list[ChatMessageResponse])
async def get_chat_history(doc_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.document_id == doc_id, ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.timestamp)
    )
    return (await db.execute(stmt)).scalars().all()

@router.post("/reset")
async def reset_system(
    doc_id: uuid.UUID = Body(...), 
    config_id: uuid.UUID = Body(...), 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Resets memory, deletes history, and clears vectordb collections."""
    from sqlalchemy import delete
    import shutil
    import os
    
    # 2. Clear Database conversation history for this document
    await db.execute(delete(ChatMessage).where(ChatMessage.document_id == doc_id, ChatMessage.user_id == current_user.id))
    await db.commit()
    
    # 3. Clear Chroma storage folder if it exists (wipe everything)
    # WARNING: This deletes all collections. If specific config reset is desired, 
    # we would use vs.delete_collection(name=collection_name).
    # For now, following 'emptied' request to clear everything.
    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    if os.path.exists(persist_dir):
        try:
            # We first close/reset Chroma connections if possible,
            # or just try to wipe the folder.
            shutil.rmtree(persist_dir)
            os.makedirs(persist_dir, exist_ok=True)
        except Exception as e:
            # Might be locked by process.
            return {"status": "partial_success", "error": f"Failed to clear disk storage: {str(e)}"}
            
    return {"status": "success", "message": "System reset complete."}