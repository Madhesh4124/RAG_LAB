import uuid
import pytest
from types import SimpleNamespace
from sqlalchemy import select
from langchain_core.documents import Document

from app.compare.schemas import RAGConfig
from app.compare.utils import derive_config_signature
from app.compare.compare_runner import _retrieve_compare_candidates
from app.models.chat import ChatMessage
from app.models.rag_config import RAGConfig as RAGConfigModel
from app.services.chunking.base import Chunk
from app.api.compare import compare_configs
from app.api.evaluation import build_message_evaluation_report


def test_rag_config_retrieval_parameters():
    config = RAGConfig(
        name="Hybrid Config",
        chunk_strategy="fixed_size",
        embedding_provider="nvidia",
        embedding_model="nvidia/nemotron-3-embed-1b",
        top_k=6,
        threshold=0.45,
        retrieval_type="hybrid",
        alpha=0.8,
        reranker_enabled=True,
        reranker_model="BAAI/bge-reranker-base",
    )
    assert config.retrieval_type == "hybrid"
    assert config.alpha == 0.8
    assert config.top_k == 6
    assert config.threshold == 0.45
    assert config.reranker_enabled is True
    assert config.reranker_model == "BAAI/bge-reranker-base"


def test_rag_config_signature_sensitivity():
    c1 = RAGConfig(
        name="Config 1",
        chunk_strategy="fixed_size",
        embedding_provider="nvidia",
        embedding_model="nvidia/nemotron-3-embed-1b",
        retrieval_type="dense",
    )
    c2 = RAGConfig(
        name="Config 2",
        chunk_strategy="fixed_size",
        embedding_provider="nvidia",
        embedding_model="nvidia/nemotron-3-embed-1b",
        retrieval_type="hybrid",
        alpha=0.4,
    )
    sig1 = derive_config_signature(c1)
    sig2 = derive_config_signature(c2)
    assert sig1 != sig2


class DummyVectorStore:
    def __init__(self, docs_and_scores):
        self.docs_and_scores = docs_and_scores

    def similarity_search_with_score(self, query, k):
        return self.docs_and_scores[:k]

    def max_marginal_relevance_search(self, query, k, fetch_k, lambda_mult=0.5):
        return [doc for doc, _ in self.docs_and_scores[:k]]

    def get(self):
        return {
            "documents": [d.page_content for d, _ in self.docs_and_scores],
            "metadatas": [d.metadata for d, _ in self.docs_and_scores],
            "ids": [f"chunk_{i}" for i in range(len(self.docs_and_scores))],
        }


def test_retrieve_compare_candidates_strategies():
    test_docs = [
        (Document(page_content="Machine learning enables AI applications.", metadata={"id": "1"}), 0.2),
        (Document(page_content="Deep neural networks require substantial computing power.", metadata={"id": "2"}), 0.4),
        (Document(page_content="Cooking recipes for Italian pasta dishes.", metadata={"id": "3"}), 0.9),
    ]
    vs = DummyVectorStore(test_docs)

    dense_cfg = RAGConfig(
        name="Dense Test",
        chunk_strategy="fixed_size",
        embedding_provider="nvidia",
        embedding_model="nvidia/nemotron-3-embed-1b",
        top_k=2,
        threshold=0.5,
        retrieval_type="dense",
    )
    candidates, filtered = _retrieve_compare_candidates("machine learning", dense_cfg, vs, user_scope="test_user")
    assert len(candidates) >= 2
    assert len(filtered) <= 2
    assert "Machine learning" in filtered[0][0].page_content

    mmr_cfg = RAGConfig(
        name="MMR Test",
        chunk_strategy="fixed_size",
        embedding_provider="nvidia",
        embedding_model="nvidia/nemotron-3-embed-1b",
        top_k=2,
        threshold=0.5,
        retrieval_type="mmr",
        lambda_mult=0.7,
    )
    candidates_mmr, filtered_mmr = _retrieve_compare_candidates("AI networks", mmr_cfg, vs, user_scope="test_user")
    assert len(filtered_mmr) <= 2

    hybrid_cfg = RAGConfig(
        name="Hybrid Test",
        chunk_strategy="fixed_size",
        embedding_provider="nvidia",
        embedding_model="nvidia/nemotron-3-embed-1b",
        top_k=2,
        threshold=0.3,
        retrieval_type="hybrid",
        alpha=0.6,
    )
    candidates_hyb, filtered_hyb = _retrieve_compare_candidates("pasta cooking", hybrid_cfg, vs, user_scope="test_user")
    assert len(filtered_hyb) > 0


class _FakeLLMClient:
    def __init__(self, reply="Generated answer"):
        self.llm = object()
        self.reply = reply
        self.calls = []

    async def generate_async(self, query, chunks):
        self.calls.append((query, len(chunks)))
        return self.reply


class _FakePipeline:
    def __init__(self, chunks_and_scores, llm_reply="Generated answer"):
        self.chunks_and_scores = chunks_and_scores
        self.llm_client = _FakeLLMClient(reply=llm_reply)
        self.embedder = None
        self.vectorstore = SimpleNamespace(
            _get_vectorstore=lambda _e: DummyVectorStore(
                [(Document(page_content=c.text, metadata=c.metadata), 0.1) for c, _ in chunks_and_scores]
            )
        )

    async def aindex_document(self, text, doc_id, metadata):
        return None

    async def aretrieve(self, query, top_k=5):
        return self.chunks_and_scores[:top_k]


@pytest.mark.anyio
async def test_compare_persists_paired_user_and_assistant_messages_for_evaluation(
    async_db_session, user_a, sample_docs, monkeypatch
):
    doc_a, _ = sample_docs
    cfg = RAGConfigModel(
        id=uuid.uuid4(),
        user_id=user_a.id,
        document_id=doc_a.id,
        name="Compare Eval Config",
        config_json={
            "chunker": {"strategy": "recursive"},
            "embedder": {"provider": "nvidia", "model": "nvidia/nemotron-3-embed-1b"},
            "retriever": {"top_k": 3, "type": "dense"},
            "vectorstore": {"type": "chroma"},
        },
    )
    async_db_session.add(cfg)
    await async_db_session.commit()

    fake_chunks = [(Chunk(id="c1", text="Alpha policy deadline is Friday.", metadata={}), 0.88)]
    monkeypatch.setattr(
        "app.api.compare.PipelineFactory.create_pipeline",
        lambda _cfg: _FakePipeline(fake_chunks, llm_reply="Friday is the deadline."),
    )

    resp = await compare_configs(
        document_id=doc_a.id,
        query="What is the deadline in alpha?",
        config_ids=[cfg.id],
        current_user=user_a,
        db=async_db_session,
    )
    assert len(resp["results"]) == 1
    msg_id = uuid.UUID(resp["results"][0]["message_id"])

    rows = (
        await async_db_session.execute(
            select(ChatMessage)
            .where(ChatMessage.document_id == doc_a.id, ChatMessage.config_id == cfg.id)
            .order_by(ChatMessage.timestamp.asc())
        )
    ).scalars().all()
    assert [r.role for r in rows] == ["user", "assistant"]
    assert rows[0].content == "What is the deadline in alpha?"
    assert rows[1].id == msg_id
    assert rows[0].timestamp <= rows[1].timestamp

    report = await build_message_evaluation_report(
        db=async_db_session,
        message_id=msg_id,
        user_id=user_a.id,
        deep=False,
    )
    assert report["message_id"] == str(msg_id)
    assert report["mode"] == "message-fast"


@pytest.mark.anyio
async def test_compare_global_query_falls_back_to_llm_when_summary_is_none(
    async_db_session, user_a, sample_docs, monkeypatch
):
    doc_a, _ = sample_docs
    cfg = RAGConfigModel(
        id=uuid.uuid4(),
        user_id=user_a.id,
        document_id=doc_a.id,
        name="Global Fallback Config",
        config_json={
            "chunker": {"strategy": "recursive"},
            "embedder": {"provider": "nvidia", "model": "nvidia/nemotron-3-embed-1b"},
            "retriever": {"top_k": 3, "type": "hybrid"},
            "vectorstore": {"type": "chroma"},
        },
    )
    async_db_session.add(cfg)
    await async_db_session.commit()

    fake_chunks = [Chunk(id="c1", text="Document discusses RAG metrics.", metadata={})]
    fake_pipeline = _FakePipeline([], llm_reply="Fallback global synthesis answer.")
    monkeypatch.setattr("app.api.compare.PipelineFactory.create_pipeline", lambda _cfg: fake_pipeline)
    monkeypatch.setattr("app.api.compare.classify_query", lambda _q: "global")

    async def _fake_summarize(**kwargs):
        return None, [(Document(page_content="Document discusses RAG metrics."), 0.75)], fake_chunks

    monkeypatch.setattr("app.api.compare._summarize_compare_context", _fake_summarize)

    resp = await compare_configs(
        document_id=doc_a.id,
        query="Summarize the whole document",
        config_ids=[cfg.id],
        current_user=user_a,
        db=async_db_session,
    )
    assert len(resp["results"]) == 1
    assert resp["results"][0]["answer"] == "Fallback global synthesis answer."
    assert len(fake_pipeline.llm_client.calls) == 1
