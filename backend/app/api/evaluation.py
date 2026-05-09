import logging
import asyncio
import time
import uuid
from copy import deepcopy
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from pydantic import BaseModel, Field

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.chat import ChatMessage
from app.models.evaluation import EvaluationResult
from app.models.rag_config import RAGConfig
from app.services.chunking.base import Chunk
from app.services.evaluation.answer_relevancy import AnswerRelevancyEvaluator
from app.services.evaluation.context_quality import ContextQualityEvaluator
from app.services.evaluation.faithfulness import FaithfulnessEvaluator
from app.services.evaluation.retrieval_metrics import build_retrieval_metrics_report
from app.services.pipeline_factory import PipelineFactory
from app.services.query_classifier import classify_query

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])
logger = logging.getLogger(__name__)


class EvaluationError(Exception):
    """Base exception for evaluation failures."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class EvaluationNotFoundError(EvaluationError):
    def __init__(self, message: str):
        super().__init__(message, status_code=404)


class EvaluationBadRequestError(EvaluationError):
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class EvaluationServiceUnavailableError(EvaluationError):
    def __init__(self, message: str):
        super().__init__(message, status_code=503)


def _is_missing_evaluation_table(exc: Exception) -> bool:
    message = str(exc).lower()
    return "no such table: evaluation_results" in message


class EvaluationReportRequest(BaseModel):
    message_id: Optional[uuid.UUID] = None
    query: Optional[str] = None
    answer: Optional[str] = None
    chunks: list[dict[str, Any] | str] = Field(default_factory=list)
    retrieval_config: Optional[dict[str, Any]] = None
    deep: bool = False


def _chunks_from_payload(raw_chunks):
    chunks = []
    for idx, item in enumerate(raw_chunks or []):
        if isinstance(item, Chunk):
            chunks.append(item)
            continue

        if isinstance(item, dict):
            if "text" not in item:
                raise EvaluationBadRequestError(f"Malformed chunk payload: missing 'text' key in element {idx}")
            metadata = dict(item.get("metadata", {}) or {})
            if "score" in item:
                metadata.setdefault("score", item.get("score"))
            chunks.append(
                Chunk(
                    text=str(item.get("text", "")),
                    metadata=metadata,
                )
            )
            continue

        chunks.append(Chunk(text=str(item), metadata={"position": idx}))
    return chunks


def score_message(
    db: AsyncSession,
    assistant_msg: ChatMessage,
    query_text: str,
    llm_client,
    chunks: list[Chunk] | None = None,
) -> EvaluationResult:
    if llm_client is None or getattr(llm_client, "llm", None) is None:
        raise EvaluationServiceUnavailableError("LLM client is unavailable for evaluation")

    parsed_chunks = chunks if chunks is not None else _chunks_from_payload(assistant_msg.retrieved_chunks or [])

    faithfulness = FaithfulnessEvaluator().evaluate(
        query=query_text,
        answer=assistant_msg.content,
        chunks=parsed_chunks,
        llm_client=llm_client,
    )
    faithfulness = faithfulness if faithfulness is not None else 0.0

    answer_relevancy = AnswerRelevancyEvaluator().evaluate(
        query=query_text,
        answer=assistant_msg.content,
        llm_client=llm_client,
    )
    answer_relevancy = answer_relevancy if answer_relevancy is not None else 0.0

    context_quality = ContextQualityEvaluator().evaluate(
        query=query_text,
        answer=assistant_msg.content,
        chunks=parsed_chunks,
        llm_client=llm_client,
    )
    context_quality = context_quality or {"context_precision": 0.0, "context_recall": 0.0}

    result = EvaluationResult(
        message_id=assistant_msg.id,
        faithfulness=faithfulness,
        answer_relevancy=answer_relevancy,
        context_precision=context_quality["context_precision"],
        context_recall=context_quality["context_recall"],
    )
    db.add(result)
    return result


def compute_answer_metrics(
    query_text: str,
    answer_text: str,
    llm_client,
    chunks: list[Chunk] | None = None,
) -> dict[str, Optional[float]]:
    if llm_client is None or getattr(llm_client, "llm", None) is None:
        return {
            "faithfulness": None,
            "answer_relevancy": None,
            "context_precision": None,
            "context_recall": None,
        }

    parsed_chunks = chunks or []

    try:
        faithfulness = FaithfulnessEvaluator().evaluate(
            query=query_text,
            answer=answer_text,
            chunks=parsed_chunks,
            llm_client=llm_client,
        )
    except Exception:
        faithfulness = None

    try:
        answer_relevancy = AnswerRelevancyEvaluator().evaluate(
            query=query_text,
            answer=answer_text,
            llm_client=llm_client,
        )
    except Exception:
        answer_relevancy = None

    try:
        context_quality = ContextQualityEvaluator().evaluate(
            query=query_text,
            answer=answer_text,
            chunks=parsed_chunks,
            llm_client=llm_client,
        )
    except Exception:
        context_quality = {}

    return {
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "context_precision": context_quality.get("context_precision"),
        "context_recall": context_quality.get("context_recall"),
    }


async def build_message_evaluation_report(
    db: AsyncSession,
    message_id: uuid.UUID,
    user_id: uuid.UUID,
    candidate_pool_size: int = 20,
    deep: bool = False,
) -> dict[str, Any]:
    started_at = time.perf_counter()
    msg_stmt = select(ChatMessage).where(ChatMessage.id == message_id, ChatMessage.user_id == user_id)
    msg = (await db.execute(msg_stmt)).scalars().first()
    if not msg:
        raise EvaluationNotFoundError("Message not found")
    if msg.role != "assistant":
        raise EvaluationBadRequestError("Evaluation is only available for assistant messages")

    query_stmt = (
        select(ChatMessage)
        .where(
            ChatMessage.document_id == msg.document_id,
            ChatMessage.config_id == msg.config_id,
            ChatMessage.user_id == user_id,
            ChatMessage.role == "user",
            ChatMessage.timestamp <= msg.timestamp,
        )
        .order_by(ChatMessage.timestamp.desc())
    )
    user_msg = (await db.execute(query_stmt)).scalars().first()
    if not user_msg:
        raise EvaluationNotFoundError("Associated user query was not found")

    config = await db.get(RAGConfig, msg.config_id)
    if not config:
        raise EvaluationNotFoundError("RAG config not found")

    pipeline_config = deepcopy(config.config_json or {})
    retrieval_config = deepcopy(pipeline_config.get("retriever", {}))
    query_mode = classify_query(user_msg.content)
    retrieved_chunks = _chunks_from_payload(msg.retrieved_chunks or [])
    eval_record = None
    try:
        eval_stmt = (
            select(EvaluationResult)
            .where(EvaluationResult.message_id == msg.id)
            .order_by(EvaluationResult.created_at.desc())
        )
        eval_record = (await db.execute(eval_stmt)).scalars().first()
    except OperationalError as exc:
        if not _is_missing_evaluation_table(exc):
            raise

    llm_client = None
    embedder = None
    candidate_chunks = retrieved_chunks

    if deep:
        vectorstore_cfg = deepcopy(pipeline_config.get("vectorstore", {}))
        if vectorstore_cfg.get("type") == "chroma":
            vectorstore_cfg["collection_name"] = f"user_{user_id}_rag_cfg_{config.id}"
            pipeline_config["vectorstore"] = vectorstore_cfg

        pipeline = PipelineFactory.create_pipeline(pipeline_config)
        llm_client = getattr(pipeline, "llm_client", None)
        embedder = getattr(pipeline, "embedder", None)
        top_k = int(retrieval_config.get("top_k", 5))
        pool_k = max(candidate_pool_size, top_k)
        candidate_results = await pipeline.aretrieve(user_msg.content, top_k=pool_k)
        candidate_chunks = [item[0] if isinstance(item, tuple) else item for item in candidate_results] or retrieved_chunks

    report = build_retrieval_metrics_report(
        query=user_msg.content,
        answer=msg.content,
        retrieved_chunks=retrieved_chunks,
        candidate_chunks=candidate_chunks,
        llm_client=llm_client,
        embedder=embedder,
        retrieval_config=retrieval_config,
        query_mode=query_mode,
    )
    report["message_id"] = str(msg.id)
    report["mode"] = "message-deep" if deep else "message-fast"
    answer_metrics = report.get("answer_metrics", {})
    if eval_record is not None:
        answer_metrics.update(
            {
                "faithfulness": eval_record.faithfulness,
                "answer_relevancy": eval_record.answer_relevancy,
                "context_precision": eval_record.context_precision,
                "context_recall": eval_record.context_recall,
            }
        )
    elif deep:
        computed_answer_metrics = compute_answer_metrics(
            query_text=user_msg.content,
            answer_text=msg.content,
            llm_client=llm_client,
            chunks=retrieved_chunks,
        )
        for key, value in computed_answer_metrics.items():
            if value is not None:
                answer_metrics[key] = value
    report["answer_metrics"] = answer_metrics
    report["timing_ms"] = round((time.perf_counter() - started_at) * 1000, 2)
    return report


def build_ad_hoc_evaluation_report(
    query: str,
    answer: str,
    chunks: list[dict[str, Any] | str],
    retrieval_config: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    parsed_chunks = _chunks_from_payload(chunks or [])
    report = build_retrieval_metrics_report(
        query=query,
        answer=answer,
        retrieved_chunks=parsed_chunks,
        candidate_chunks=parsed_chunks,
        llm_client=None,
        embedder=None,
        retrieval_config=retrieval_config or {},
    )
    report["mode"] = "ad_hoc"
    return report


async def score_message_by_id(db: AsyncSession, message_id: uuid.UUID, user_id: uuid.UUID) -> EvaluationResult:
    msg_stmt = select(ChatMessage).where(ChatMessage.id == message_id, ChatMessage.user_id == user_id)
    msg = (await db.execute(msg_stmt)).scalars().first()
    if not msg:
        raise EvaluationNotFoundError("Message not found")
    if msg.role != "assistant":
        raise EvaluationBadRequestError("Scoring is only available for assistant messages")

    query_stmt = (
        select(ChatMessage)
        .where(
            ChatMessage.document_id == msg.document_id,
            ChatMessage.config_id == msg.config_id,
            ChatMessage.user_id == user_id,
            ChatMessage.role == "user",
            ChatMessage.timestamp <= msg.timestamp,
        )
        .order_by(ChatMessage.timestamp.desc())
    )
    user_msg = (await db.execute(query_stmt)).scalars().first()
    if not user_msg:
        raise EvaluationNotFoundError("Associated user query was not found")

    config = await db.get(RAGConfig, msg.config_id)
    if not config:
        raise EvaluationNotFoundError("RAG config not found")

    pipeline_config = deepcopy(config.config_json or {})
    vectorstore_cfg = deepcopy(pipeline_config.get("vectorstore", {}))
    if vectorstore_cfg.get("type") == "chroma":
        vectorstore_cfg["collection_name"] = f"user_{user_id}_rag_cfg_{config.id}"
        pipeline_config["vectorstore"] = vectorstore_cfg

    pipeline = PipelineFactory.create_pipeline(pipeline_config)
    llm_client = getattr(pipeline, "llm_client", None)
    chunks = _chunks_from_payload(msg.retrieved_chunks or [])
    result = score_message(
        db=db,
        assistant_msg=msg,
        query_text=user_msg.content,
        llm_client=llm_client,
        chunks=chunks,
    )
    return result


@router.post("/score")
async def evaluate_score(
    message_id: uuid.UUID = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await score_message_by_id(db=db, message_id=message_id, user_id=current_user.id)
    except EvaluationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during evaluation")
        raise HTTPException(status_code=500, detail="Internal server error during evaluation")

    await db.commit()
    await db.refresh(result)

    return {
        "message_id": str(result.message_id),
        "faithfulness": result.faithfulness,
        "answer_relevancy": result.answer_relevancy,
        "context_precision": result.context_precision,
        "context_recall": result.context_recall,
        "created_at": result.created_at,
    }


@router.post("/faithfulness")
async def evaluate_faithfulness_alias(
    message_id: uuid.UUID = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    return await evaluate_score(message_id=message_id, db=db)


@router.post("/report")
async def evaluate_report(
    payload: EvaluationReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        if payload.message_id:
            if payload.deep:
                timeout_seconds = float(
                    __import__("os").getenv("DEEP_EVALUATION_TIMEOUT_SECONDS", "25")
                )
                try:
                    return await asyncio.wait_for(
                        build_message_evaluation_report(
                            db=db,
                            message_id=payload.message_id,
                            user_id=current_user.id,
                            deep=True,
                        ),
                        timeout=timeout_seconds,
                    )
                except asyncio.TimeoutError:
                    raise EvaluationServiceUnavailableError(
                        f"Deep evaluation timed out after {int(timeout_seconds)} seconds"
                    )

            return await build_message_evaluation_report(
                db=db,
                message_id=payload.message_id,
                user_id=current_user.id,
                deep=False,
            )

        if not payload.query:
            raise EvaluationBadRequestError("Either message_id or query must be provided")

        return build_ad_hoc_evaluation_report(
            query=payload.query,
            answer=payload.answer or "",
            chunks=payload.chunks or [],
            retrieval_config=payload.retrieval_config or {},
        )
    except EvaluationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    except Exception:
        logger.exception("Unexpected error during evaluation report generation")
        raise HTTPException(status_code=500, detail="Internal server error during evaluation report generation")
