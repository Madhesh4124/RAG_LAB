import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.chat import ChatMessage
from app.models.evaluation import EvaluationResult
from app.models.metrics import Metrics
from app.models.rag_config import RAGConfig

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/summary")
def get_metrics_summary(document_id: uuid.UUID = Query(...), db: Session = Depends(get_db)):
    configs = db.execute(
        select(RAGConfig).where(RAGConfig.document_id == document_id)
    ).scalars().all()
    if not configs:
        raise HTTPException(status_code=404, detail="No configs found for document")

    config_map = {cfg.id: cfg.name for cfg in configs}

    all_messages = db.execute(
        select(ChatMessage)
        .where(ChatMessage.document_id == document_id)
        .order_by(ChatMessage.timestamp)
    ).scalars().all()

    assistant_messages = [msg for msg in all_messages if msg.role == "assistant"]

    latest_user_by_config = {}
    paired_query_by_assistant = {}
    for msg in all_messages:
        if msg.role == "user":
            latest_user_by_config[msg.config_id] = msg
        elif msg.role == "assistant":
            paired_query_by_assistant[msg.id] = latest_user_by_config.get(msg.config_id)

    metric_rows = db.execute(
        select(Metrics).where(Metrics.message_id.in_([msg.id for msg in assistant_messages]))
    ).scalars().all() if assistant_messages else []
    metric_map = {row.message_id: row for row in metric_rows}

    eval_rows = db.execute(
        select(EvaluationResult).where(EvaluationResult.message_id.in_([msg.id for msg in assistant_messages]))
    ).scalars().all() if assistant_messages else []
    eval_map = {}
    for row in eval_rows:
        current = eval_map.get(row.message_id)
        if current is None or row.created_at > current.created_at:
            eval_map[row.message_id] = row

    queries = []
    agg = defaultdict(lambda: {
        "count": 0,
        "response_time_sum": 0.0,
        "avg_similarity_sum": 0.0,
        "faithfulness_sum": 0.0,
        "faithfulness_count": 0,
        "answer_relevancy_sum": 0.0,
        "answer_relevancy_count": 0,
        "context_precision_sum": 0.0,
        "context_precision_count": 0,
        "context_recall_sum": 0.0,
        "context_recall_count": 0,
    })

    for assistant in assistant_messages:
        metrics = metric_map.get(assistant.id)
        evaluation = eval_map.get(assistant.id)

        user_query = paired_query_by_assistant.get(assistant.id)
        query_text = user_query.content if user_query else ""

        query_item = {
            "message_id": str(assistant.id),
            "query_text": query_text,
            "config_id": str(assistant.config_id),
            "config_name": config_map.get(assistant.config_id, "Unknown Config"),
            "faithfulness": evaluation.faithfulness if evaluation else None,
            "answer_relevancy": evaluation.answer_relevancy if evaluation else None,
            "context_precision": evaluation.context_precision if evaluation else None,
            "context_recall": evaluation.context_recall if evaluation else None,
            "response_time_ms": metrics.total_time_ms if metrics else None,
            "avg_similarity": metrics.avg_similarity if metrics else None,
        }
        queries.append(query_item)

        bucket = agg[assistant.config_id]
        bucket["count"] += 1
        if metrics and metrics.total_time_ms is not None:
            bucket["response_time_sum"] += float(metrics.total_time_ms)
        if metrics and metrics.avg_similarity is not None:
            bucket["avg_similarity_sum"] += float(metrics.avg_similarity)

        if evaluation and evaluation.faithfulness is not None:
            bucket["faithfulness_sum"] += float(evaluation.faithfulness)
            bucket["faithfulness_count"] += 1
        if evaluation and evaluation.answer_relevancy is not None:
            bucket["answer_relevancy_sum"] += float(evaluation.answer_relevancy)
            bucket["answer_relevancy_count"] += 1
        if evaluation and evaluation.context_precision is not None:
            bucket["context_precision_sum"] += float(evaluation.context_precision)
            bucket["context_precision_count"] += 1
        if evaluation and evaluation.context_recall is not None:
            bucket["context_recall_sum"] += float(evaluation.context_recall)
            bucket["context_recall_count"] += 1

    per_config = []
    for cfg in configs:
        bucket = agg[cfg.id]
        count = bucket["count"] or 1
        per_config.append(
            {
                "config_id": str(cfg.id),
                "config_name": cfg.name,
                "total_queries": bucket["count"],
                "avg_response_time_ms": bucket["response_time_sum"] / count,
                "avg_similarity": bucket["avg_similarity_sum"] / count,
                "avg_faithfulness": (
                    bucket["faithfulness_sum"] / bucket["faithfulness_count"]
                    if bucket["faithfulness_count"]
                    else None
                ),
                "avg_answer_relevancy": (
                    bucket["answer_relevancy_sum"] / bucket["answer_relevancy_count"]
                    if bucket["answer_relevancy_count"]
                    else None
                ),
                "avg_context_precision": (
                    bucket["context_precision_sum"] / bucket["context_precision_count"]
                    if bucket["context_precision_count"]
                    else None
                ),
                "avg_context_recall": (
                    bucket["context_recall_sum"] / bucket["context_recall_count"]
                    if bucket["context_recall_count"]
                    else None
                ),
            }
        )

    return {
        "document_id": str(document_id),
        "per_config": per_config,
        "queries": queries,
    }
