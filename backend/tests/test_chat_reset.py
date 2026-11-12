import uuid
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.chat import reset_system
from app.models.chat import ChatMessage
from app.models.document_summary import DocumentSummary
from app.models.rag_config import RAGConfig
from app.services.pipeline_manager import PipelineManager, _CacheEntry
from app.services.vectorstore.chroma_store import ChromaStore


@pytest.mark.anyio
async def test_reset_system_scopes_by_config_and_clears_caches(
    async_db_session, user_a, sample_config_and_chat, tmp_path, monkeypatch
):
    cfg_a, msg_a = sample_config_and_chat
    doc_a_id = cfg_a.document_id

    # Create a second config and message on the same document that must NOT be deleted.
    cfg_b = RAGConfig(
        user_id=user_a.id,
        document_id=doc_a_id,
        name="cfg-b",
        config_json={"vectorstore": {"type": "chroma"}},
        is_active=True,
    )
    async_db_session.add(cfg_b)
    await async_db_session.flush()

    msg_b = ChatMessage(
        user_id=user_a.id,
        document_id=doc_a_id,
        config_id=cfg_b.id,
        role="assistant",
        content="keep me",
        retrieved_chunks=[],
    )
    sum_a = DocumentSummary(
        user_id=user_a.id,
        document_id=doc_a_id,
        config_id=cfg_a.id,
        summary="Summary A",
    )
    sum_b = DocumentSummary(
        user_id=user_a.id,
        document_id=doc_a_id,
        config_id=cfg_b.id,
        summary="Summary B",
    )
    async_db_session.add_all([msg_b, sum_a, sum_b])
    await async_db_session.commit()

    cache_key = f"{user_a.id}:{cfg_a.id}"
    memory_cleared = {"called": False}
    fake_memory = SimpleNamespace(clear=lambda: memory_cleared.__setitem__("called", True))
    PipelineManager._cache[cache_key] = _CacheEntry(
        pipeline=SimpleNamespace(memory=fake_memory),
        config_hash="hash-a",
    )

    chroma_deleted = []
    monkeypatch.setattr(
        ChromaStore,
        "delete_document",
        lambda self, doc_id: chroma_deleted.append((self.collection_name, doc_id)),
    )

    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path))
    bm25_file = tmp_path / f"bm25_user_{user_a.id}_rag_cfg_{cfg_a.id}.json"
    bm25_file.write_text("[]", encoding="utf-8")

    try:
        res = await reset_system(
            doc_id=doc_a_id,
            config_id=cfg_a.id,
            current_user=user_a,
            db=async_db_session,
        )
        assert res["status"] == "success"
        assert res["deleted_messages"] == 1
        assert memory_cleared["called"] is True
        assert cache_key not in PipelineManager._cache
        assert chroma_deleted == [(f"user_{user_a.id}_rag_cfg_{cfg_a.id}", str(doc_a_id))]
        assert not bm25_file.exists()

        remaining_msgs = (
            await async_db_session.execute(
                select(ChatMessage).where(ChatMessage.document_id == doc_a_id)
            )
        ).scalars().all()
        assert [m.id for m in remaining_msgs] == [msg_b.id]

        remaining_sums = (
            await async_db_session.execute(
                select(DocumentSummary).where(DocumentSummary.document_id == doc_a_id)
            )
        ).scalars().all()
        assert [s.id for s in remaining_sums] == [sum_b.id]
    finally:
        PipelineManager._cache.pop(cache_key, None)


@pytest.mark.anyio
async def test_reset_system_rejects_other_users_config(async_db_session, user_b, sample_config_and_chat):
    cfg_a, _ = sample_config_and_chat
    with pytest.raises(HTTPException) as exc:
        await reset_system(
            doc_id=cfg_a.document_id,
            config_id=cfg_a.id,
            current_user=user_b,
            db=async_db_session,
        )
    assert exc.value.status_code == 404
