import asyncio
import json
import logging
import uuid
import pytest

from app.api.chat import chat_stream_endpoint
from app.services.chunking.base import Chunk
from app.services.pipeline_manager import PipelineManager
from app.services.rate_limiter import RateLimitExceededException
from app.services.summary_service import SummaryService


class _AsyncSessionCtx:
    def __init__(self, adapter):
        self._adapter = adapter

    async def __aenter__(self):
        return self._adapter

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _parse_sse_events(chunks: list[bytes | str]) -> list[dict]:
    events = []
    for raw in chunks:
        text = raw.decode() if isinstance(raw, bytes) else raw
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                events.append(json.loads(line[5:].strip()))
    return events


@pytest.mark.anyio
async def test_chat_stream_global_cache_hit_skips_llm_rate_limit(
    async_db_session, user_a, sample_config_and_chat, monkeypatch
):
    cfg, _ = sample_config_and_chat
    doc_id = cfg.document_id

    monkeypatch.setattr("app.api.chat.AsyncSessionLocal", lambda: _AsyncSessionCtx(async_db_session))
    monkeypatch.setattr("app.api.chat.classify_query", lambda _q: "global")

    async def _fake_get_summary(**kwargs):
        return (
            "This is a complete cached document summary with enough content to satisfy the minimum length "
            "and end cleanly with proper punctuation."
        )

    monkeypatch.setattr(SummaryService, "get_summary", _fake_get_summary)

    enforced = []
    recorded = []

    class _FakeLimiter:
        def __init__(self, _db):
            pass

        async def enforce_rate_limit(self, scope_key, op):
            enforced.append((scope_key, op))
            raise RateLimitExceededException(scope_key, op, "should not be enforced on cached summary")

        async def record_call(self, scope_key, op, user_id):
            recorded.append((scope_key, op, user_id))

    monkeypatch.setattr("app.api.chat.DatabaseRateLimiter", _FakeLimiter)

    class _FakePipeline:
        llm_client = object()

        async def aretrieve(self, query, top_k=5):
            return [(Chunk(id="c1", text="Summary evidence chunk.", metadata={}), 0.9)]

    monkeypatch.setattr(PipelineManager, "get_pipeline", classmethod(lambda cls, k, c: _FakePipeline()))

    resp = await chat_stream_endpoint(
        query="Summarize the whole document",
        doc_id=doc_id,
        doc_ids=None,
        config_id=cfg.id,
        current_user=user_a,
    )
    raw_chunks = [part async for part in resp.body_iterator]
    events = _parse_sse_events(raw_chunks)

    assert enforced == []
    assert recorded == []
    assert any(e["type"] == "token" and "cached document summary" in e["content"] for e in events)
    done = [e for e in events if e["type"] == "done"]
    assert len(done) == 1
    assert done[0]["persisted"] is True
    assert done[0]["message_id"] is not None


@pytest.mark.anyio
async def test_chat_stream_db_failure_logs_and_emits_unpersisted_warning(
    async_db_session, user_a, sample_config_and_chat, monkeypatch, caplog
):
    cfg, _ = sample_config_and_chat
    doc_id = cfg.document_id

    class _FailingWriteSession:
        def add(self, _obj):
            pass

        async def commit(self):
            raise RuntimeError("simulated disk full")

        async def refresh(self, _obj):
            pass

    call_count = {"n": 0}

    def _session_factory():
        call_count["n"] += 1
        # 1: read_db, 2: limiter enforce, 3: limiter record_call, 4: write_db
        if call_count["n"] == 4:
            return _AsyncSessionCtx(_FailingWriteSession())
        return _AsyncSessionCtx(async_db_session)

    monkeypatch.setattr("app.api.chat.AsyncSessionLocal", _session_factory)
    monkeypatch.setattr("app.api.chat.classify_query", lambda _q: "local")

    class _FakeLimiter:
        def __init__(self, _db):
            pass

        async def enforce_rate_limit(self, scope_key, op):
            return None

        async def record_call(self, scope_key, op, user_id):
            return None

    monkeypatch.setattr("app.api.chat.DatabaseRateLimiter", _FakeLimiter)

    class _FakePipeline:
        llm_client = object()

        async def aretrieve(self, query, top_k=5):
            return [(Chunk(id="c1", text="Chunk text", metadata={}), 0.8)]

        async def agenerate_stream(self, query, chunks):
            yield "Hello "
            yield "world"

    monkeypatch.setattr(PipelineManager, "get_pipeline", classmethod(lambda cls, k, c: _FakePipeline()))

    with caplog.at_level(logging.ERROR):
        resp = await chat_stream_endpoint(
            query="What is in the doc?",
            doc_id=doc_id,
            doc_ids=None,
            config_id=cfg.id,
            current_user=user_a,
        )
        raw_chunks = [part async for part in resp.body_iterator]

    events = _parse_sse_events(raw_chunks)
    done = [e for e in events if e["type"] == "done"]
    assert len(done) == 1
    assert done[0]["message_id"] is None
    assert done[0]["persisted"] is False
    assert "saving to chat history failed" in done[0]["warning"].lower()
    assert any("Failed to persist streamed chat messages" in rec.message for rec in caplog.records)


@pytest.mark.anyio
async def test_chat_stream_cancelled_after_token_records_llm_usage(
    async_db_session, user_a, sample_config_and_chat, monkeypatch
):
    cfg, _ = sample_config_and_chat
    doc_id = cfg.document_id

    monkeypatch.setattr("app.api.chat.AsyncSessionLocal", lambda: _AsyncSessionCtx(async_db_session))
    monkeypatch.setattr("app.api.chat.classify_query", lambda _q: "local")

    recorded = []

    class _FakeLimiter:
        def __init__(self, _db):
            pass

        async def enforce_rate_limit(self, scope_key, op):
            return None

        async def record_call(self, scope_key, op, user_id):
            recorded.append((scope_key, op, user_id))

    monkeypatch.setattr("app.api.chat.DatabaseRateLimiter", _FakeLimiter)

    class _FakePipeline:
        llm_client = object()

        async def aretrieve(self, query, top_k=5):
            return [(Chunk(id="c1", text="Chunk text", metadata={}), 0.8)]

        async def agenerate_stream(self, query, chunks):
            yield "First token"
            raise asyncio.CancelledError()

    monkeypatch.setattr(PipelineManager, "get_pipeline", classmethod(lambda cls, k, c: _FakePipeline()))

    resp = await chat_stream_endpoint(
        query="Explain chunk",
        doc_id=doc_id,
        doc_ids=None,
        config_id=cfg.id,
        current_user=user_a,
    )

    with pytest.raises(asyncio.CancelledError):
        async for _part in resp.body_iterator:
            pass

    assert len(recorded) == 1
    assert recorded[0] == (f"user:{user_a.id}", "llm", user_a.id)
