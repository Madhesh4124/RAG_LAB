import logging
import uuid
from copy import deepcopy

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
from app.services.pipeline_factory import PipelineFactory

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


def _chunks_from_payload(raw_chunks):
    chunks = []
    for idx, item in enumerate(raw_chunks or []):
        if isinstance(item, Chunk):
            chunks.append(item)
            continue

        if isinstance(item, dict):
            if "text" not in item:
                raise EvaluationBadRequestError(f"Malformed chunk payload: missing 'text' key in element {idx}")
            chunks.append(
                Chunk(
                    text=str(item.get("text", "")),
                    metadata=item.get("metadata", {}),
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
