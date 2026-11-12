import threading
import time
import pytest
from sqlalchemy import select

from app.models.document_summary import DocumentSummary
from app.services.chunking.base import Chunk
from app.services.pipeline_manager import PipelineManager
from app.services.summary_service import SummaryService
from app.utils.timing import PipelineTimer


@pytest.mark.anyio
async def test_summary_service_does_not_return_or_keep_truncated_fallback(
    async_db_session, user_a, sample_config_and_chat, monkeypatch
):
    cfg, _ = sample_config_and_chat
    DocumentSummary.__table__.create(bind=async_db_session._sync.get_bind(), checkfirst=True)

    # Seed a stale truncated summary in DB.
    stale = DocumentSummary(
        user_id=user_a.id,
        document_id=cfg.document_id,
        config_id=cfg.id,
        summary="Incomplete cut off mid sentence",
    )
    async_db_session.add(stale)
    await async_db_session.commit()

    # Case 1: regeneration fails -> must return None (NOT stale truncated) and clear stale DB row
    async def _fail_regen(_chunks, _llm):
        return ""

    monkeypatch.setattr(SummaryService, "generate_doc_summary", _fail_regen)
    res = await SummaryService.ensure_precomputed_summary(
        db=async_db_session,
        user_id=user_a.id,
        document_id=cfg.document_id,
        config_id=cfg.id,
        chunks=[Chunk(text="Alpha body.", metadata={})],
        llm_client=object(),
    )
    assert res is None
    rows = (
        await async_db_session.execute(
            select(DocumentSummary).where(DocumentSummary.document_id == cfg.document_id)
        )
    ).scalars().all()
    assert rows == []

    # Case 2: regeneration produces another truncated string -> must NOT persist or return it
    async def _truncated_regen(_chunks, _llm):
        return "Another partial output without terminal punctuation"

    monkeypatch.setattr(SummaryService, "generate_doc_summary", _truncated_regen)
    res2 = await SummaryService.ensure_precomputed_summary(
        db=async_db_session,
        user_id=user_a.id,
        document_id=cfg.document_id,
        config_id=cfg.id,
        chunks=[Chunk(text="Alpha body.", metadata={})],
        llm_client=object(),
    )
    assert res2 is None
    rows2 = (
        await async_db_session.execute(
            select(DocumentSummary).where(DocumentSummary.document_id == cfg.document_id)
        )
    ).scalars().all()
    assert rows2 == []


@pytest.mark.anyio
async def test_pipeline_manager_bounds_and_cleans_indexing_locks(monkeypatch):
    monkeypatch.setattr("app.services.pipeline_manager._MAX_INDEXING_LOCKS", 3)
    PipelineManager.clear_cache()
    PipelineManager._indexing_locks.clear()

    try:
        l1 = await PipelineManager.get_indexing_lock("k1")
        await l1.acquire()  # Held lock must NOT be evicted
        l2 = await PipelineManager.get_indexing_lock("k2")
        l3 = await PipelineManager.get_indexing_lock("k3")
        l4 = await PipelineManager.get_indexing_lock("k4")

        assert len(PipelineManager._indexing_locks) <= 3
        assert "k1" in PipelineManager._indexing_locks
        assert l2 is not None and l3 is not None and l4 is not None

        # Unlocked key gets pruned on invalidate(); locked key remains until released
        PipelineManager.invalidate("k3")
        assert "k3" not in PipelineManager._indexing_locks
        PipelineManager.invalidate("k1")
        assert "k1" in PipelineManager._indexing_locks

        l1.release()
        PipelineManager.clear_cache()
        assert len(PipelineManager._indexing_locks) == 0
    finally:
        for lock in list(PipelineManager._indexing_locks.values()):
            if lock.locked():
                lock.release()
        PipelineManager._indexing_locks.clear()


def test_pipeline_timer_thread_isolated_start_times():
    timer = PipelineTimer()
    errors = []

    def _worker(delay: float):
        try:
            timer.start("retrieval_time_ms")
            time.sleep(delay)
            timer.stop("retrieval_time_ms")
            _ = timer.to_metrics_dict()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=_worker, args=(0.01 * (i % 3 + 1),)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert errors == []
    timings = timer.to_metrics_dict()
    assert timings["retrieval_time_ms"] > 0.0
    assert timings["total_time_ms"] >= timings["retrieval_time_ms"]


@pytest.mark.anyio
async def test_config_is_active_status_filtering_and_runtime_enforcement(
    async_db_session, user_a, sample_config_and_chat
):
    from fastapi import HTTPException
    from app.api.config import list_configs, set_config_status
    from app.api.chat import PrepareChatRequest, chat_endpoint, prepare_chat_session
    from app.api.compare import compare_configs
    from app.services.pipeline_manager import _CacheEntry

    cfg, _ = sample_config_and_chat
    cache_key = f"{user_a.id}:{cfg.id}"
    PipelineManager._cache[cache_key] = _CacheEntry(pipeline=object(), config_hash="h")

    try:
        updated = await set_config_status(
            config_id=cfg.id,
            is_active=False,
            current_user=user_a,
            db=async_db_session,
        )
        assert updated.is_active is False
        assert cache_key not in PipelineManager._cache

        active_only = await list_configs(doc_id=cfg.document_id, include_inactive=False, current_user=user_a, db=async_db_session)
        assert active_only == []

        with_inactive = await list_configs(doc_id=cfg.document_id, include_inactive=True, current_user=user_a, db=async_db_session)
        assert [c.id for c in with_inactive] == [cfg.id]

        with pytest.raises(HTTPException) as exc1:
            await prepare_chat_session(
                payload=PrepareChatRequest(document_id=cfg.document_id, config_id=cfg.id),
                background_tasks=None,
                current_user=user_a,
                db=async_db_session,
            )
        assert exc1.value.status_code == 400

        with pytest.raises(HTTPException) as exc2:
            await chat_endpoint(
                query="hi",
                doc_id=cfg.document_id,
                config_id=cfg.id,
                current_user=user_a,
                db=async_db_session,
                rate_limiter=type("L", (), {"build_scope_key": lambda self, user_id: f"u:{user_id}"})(),
            )
        assert exc2.value.status_code == 400

        with pytest.raises(HTTPException) as exc3:
            await compare_configs(
                document_id=cfg.document_id,
                query="hi",
                config_ids=[cfg.id],
                current_user=user_a,
                db=async_db_session,
            )
        assert exc3.value.status_code == 400

        res_none = await compare_configs(
            document_id=cfg.document_id,
            query="hi",
            config_ids=None,
            current_user=user_a,
            db=async_db_session,
        )
        assert res_none["results"] == []
    finally:
        PipelineManager._cache.pop(cache_key, None)


@pytest.mark.anyio
async def test_upload_document_returns_201_then_200_on_duplicate(async_db_session, user_a):
    import httpx
    from fastapi import FastAPI
    from app.api.documents import router as docs_router
    from app.auth import get_current_user
    from app.database import get_db

    test_app = FastAPI()
    test_app.include_router(docs_router)
    test_app.dependency_overrides[get_db] = lambda: async_db_session
    test_app.dependency_overrides[get_current_user] = lambda: user_a

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as client:
        resp1 = await client.post(
            "/api/documents/upload",
            files={"file": ("notes.txt", b"unique phase3 document body", "text/plain")},
        )
        resp2 = await client.post(
            "/api/documents/upload",
            files={"file": ("notes.txt", b"unique phase3 document body", "text/plain")},
        )

    assert resp1.status_code == 201
    assert resp2.status_code == 200
    assert resp1.json()["id"] == resp2.json()["id"]


@pytest.mark.anyio
async def test_reset_system_deletes_associated_evaluation_reports(
    async_db_session, user_a, sample_config_and_chat, monkeypatch
):
    from app.api.chat import reset_system
    from app.models.evaluation_report import EvaluationReport
    from app.services.vectorstore.chroma_store import ChromaStore

    EvaluationReport.__table__.create(bind=async_db_session._sync.get_bind(), checkfirst=True)
    cfg, msg = sample_config_and_chat

    bound_report = EvaluationReport(
        user_id=user_a.id,
        message_id=msg.id,
        mode="message-fast",
        report_json='{"ok": true}',
    )
    ad_hoc_report = EvaluationReport(
        user_id=user_a.id,
        message_id=None,
        mode="ad_hoc",
        report_json='{"ad_hoc": true}',
    )
    async_db_session.add_all([bound_report, ad_hoc_report])
    await async_db_session.commit()

    monkeypatch.setattr(ChromaStore, "delete_document", lambda self, doc_id: None)
    await reset_system(doc_id=cfg.document_id, config_id=cfg.id, current_user=user_a, db=async_db_session)

    remaining = (await async_db_session.execute(select(EvaluationReport))).scalars().all()
    assert [r.id for r in remaining] == [ad_hoc_report.id]

