import asyncio
import time
import pytest
from fastapi import BackgroundTasks

from app.api.chat import PrepareChatRequest, _run_indexing_background, prepare_chat_session
from app.services.indexing_jobs import IndexingJobStore, IndexingState


def test_indexing_job_store_enforces_state_transitions():
    job_id = IndexingJobStore.create(doc_id="d1", config_id="c1", user_id="u1", doc_key="d1")
    try:
        job = IndexingJobStore.get(job_id)
        assert job is not None
        assert job.status == IndexingState.PENDING.value

        # Valid: pending -> indexing -> ready
        assert IndexingJobStore.update(job_id, status="indexing", progress_pct=50) is True
        assert IndexingJobStore.update(job_id, status="ready", progress_pct=100) is True
        assert IndexingJobStore.get(job_id).status == IndexingState.READY.value

        # Invalid: terminal ready cannot transition back to indexing/failed/pending
        assert IndexingJobStore.update(job_id, status="indexing", progress_pct=10) is False
        assert IndexingJobStore.update(job_id, status="failed", error="oops") is False
        assert IndexingJobStore.get(job_id).status == IndexingState.READY.value
        assert IndexingJobStore.get(job_id).progress_pct == 100
    finally:
        IndexingJobStore._jobs.pop(job_id, None)


def test_indexing_job_store_does_not_evict_active_jobs_at_terminal_ttl():
    active_id = IndexingJobStore.create(doc_id="d1", config_id="c1", user_id="u1")
    done_id = IndexingJobStore.create(doc_id="d2", config_id="c2", user_id="u1")
    try:
        IndexingJobStore.update(active_id, status="indexing", progress_pct=20)
        IndexingJobStore.update(done_id, status="ready", progress_pct=100)

        old_time = time.monotonic() - (IndexingJobStore._TTL_SECONDS + 60)
        IndexingJobStore.get(active_id).created_at = old_time
        IndexingJobStore.get(active_id).updated_at = old_time
        IndexingJobStore.get(done_id).created_at = old_time
        IndexingJobStore.get(done_id).updated_at = old_time

        extra_id = IndexingJobStore.create(doc_id="d3", config_id="c3", user_id="u1")
        try:
            assert IndexingJobStore.get(done_id) is None
            assert IndexingJobStore.get(active_id) is not None
        finally:
            IndexingJobStore._jobs.pop(extra_id, None)
    finally:
        IndexingJobStore._jobs.pop(active_id, None)
        IndexingJobStore._jobs.pop(done_id, None)


@pytest.mark.anyio
async def test_run_indexing_background_marks_failed_on_cancellation(monkeypatch):
    job_id = IndexingJobStore.create(doc_id="d1", config_id="c1", user_id="u1")
    try:
        def raise_cancelled(*args, **kwargs):
            raise asyncio.CancelledError()

        monkeypatch.setattr("app.services.pipeline_manager.PipelineManager.get_pipeline", raise_cancelled)

        with pytest.raises(asyncio.CancelledError):
            await _run_indexing_background(
                job_id=job_id,
                docs=[],
                pipeline_config={},
                user_id="u1",
                config_id="c1",
            )

        job = IndexingJobStore.get(job_id)
        assert job.status == IndexingState.FAILED.value
        assert "cancelled" in (job.error or "").lower()
    finally:
        IndexingJobStore._jobs.pop(job_id, None)


@pytest.mark.anyio
async def test_prepare_chat_session_deduplicates_active_jobs_and_no_duplicate_summary_task(
    async_db_session,
    user_a,
    sample_config_and_chat,
    monkeypatch,
):
    cfg, msg = sample_config_and_chat
    monkeypatch.setenv("PRECOMPUTE_SUMMARIES_ON_PREPARE", "1")

    bg1 = BackgroundTasks()
    resp1 = await prepare_chat_session(
        payload=PrepareChatRequest(document_id=msg.document_id, config_id=cfg.id),
        background_tasks=bg1,
        current_user=user_a,
        db=async_db_session,
    )
    try:
        assert resp1["status"] == "pending"
        # Only _run_indexing_background should be scheduled (no duplicate _precompute_summary_background)
        assert len(bg1.tasks) == 1

        bg2 = BackgroundTasks()
        resp2 = await prepare_chat_session(
            payload=PrepareChatRequest(document_id=msg.document_id, config_id=cfg.id),
            background_tasks=bg2,
            current_user=user_a,
            db=async_db_session,
        )
        assert resp2["job_id"] == resp1["job_id"]
        assert len(bg2.tasks) == 0
    finally:
        IndexingJobStore._jobs.pop(resp1["job_id"], None)
