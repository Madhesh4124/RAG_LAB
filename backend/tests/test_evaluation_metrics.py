import datetime
import pytest
from app.services.chunking.base import Chunk
from app.services.evaluation.answer_relevancy import AnswerRelevancyEvaluator
from app.services.evaluation.context_quality import ContextQualityEvaluator
from app.services.evaluation.faithfulness import FaithfulnessEvaluator
from app.services.evaluation.retrieval_metrics import (
    _parse_bool_list,
    build_retrieval_metrics_report,
    unified_deep_evaluation,
)
from app.models.chat import ChatMessage
from app.services.pipeline_factory import PipelineFactory
from app.api.evaluation import build_message_evaluation_report, EvaluationServiceUnavailableError


def test_retrieval_report_preserves_scores_from_payload_dicts():
    report = build_retrieval_metrics_report(
        query="alpha project deadline",
        answer="The project deadline is Friday.",
        retrieved_chunks=[
            {"text": "The alpha project deadline is Friday.", "score": 0.82},
            {"text": "Unrelated background note.", "score": 0.24},
        ],
    )

    metrics = report["retrieval_metrics"]
    judgments = report["chunk_judgments"]

    assert metrics["avg_similarity"] == 0.53
    assert judgments[0]["score"] == 0.82
    assert judgments[1]["score"] == 0.24


def test_retrieval_report_preserves_scores_from_chunk_metadata():
    report = build_retrieval_metrics_report(
        query="alpha project deadline",
        answer="The project deadline is Friday.",
        retrieved_chunks=[
            Chunk(text="The alpha project deadline is Friday.", metadata={"score": 0.9}),
            Chunk(text="Unrelated background note.", metadata={"raw_score": 0.4}),
        ],
    )

    assert report["retrieval_metrics"]["avg_similarity"] == 0.65
    assert [item["score"] for item in report["chunk_judgments"]] == [0.9, 0.4]


def test_bool_list_parsers_treat_false_strings_as_false():
    assert _parse_bool_list('["true", "false", false]', expected_len=3) == [True, False, False]
    assert ContextQualityEvaluator._parse_bool_list('["true", "false", false]', expected_len=3) == [
        True,
        False,
        False,
    ]


def test_llm_judge_score_parsers_do_not_grab_rubric_zero():
    response = "The answer is supported. On the 0.0 to 1.0 scale, score: 0.875"

    assert FaithfulnessEvaluator._parse_score(response) == 0.875
    assert AnswerRelevancyEvaluator._parse_score(response) == 0.875
    assert ContextQualityEvaluator._parse_score(response) == 0.875


def test_llm_judge_score_parsers_accept_json_scores():
    assert FaithfulnessEvaluator._parse_score('{"score": 0.7}') == 0.7
    assert AnswerRelevancyEvaluator._parse_score('{"answer_relevancy": 0.8}') == 0.8
    assert ContextQualityEvaluator._parse_score('{"context_recall": 0.9}') == 0.9


def test_unified_deep_evaluation_parses_json():
    class MockResponse:
        def __init__(self, content):
            self.content = content

    class MockLLM:
        def invoke(self, prompt):
            return MockResponse(
                '{\n'
                '  "retrieved_relevance": [true, false],\n'
                '  "candidate_relevance": [true, false, true],\n'
                '  "faithfulness": 0.85,\n'
                '  "answer_relevancy": 0.95,\n'
                '  "context_recall": 0.75\n'
                '}'
            )

    class MockLLMClient:
        def __init__(self):
            self.llm = MockLLM()

    result = unified_deep_evaluation(
        query="test query",
        answer="test answer",
        retrieved_chunks=["chunk 1", "chunk 2"],
        candidate_chunks=["chunk 1", "chunk 2", "chunk 3"],
        llm_client=MockLLMClient()
    )

    assert result["retrieved_flags"] == [True, False]
    assert result["candidate_flags"] == [True, False, True]
    assert result["faithfulness"] == 0.85
    assert result["answer_relevancy"] == 0.95
    assert result["context_recall"] == 0.75


def test_unified_deep_evaluation_strips_markdown():
    class MockResponse:
        def __init__(self, content):
            self.content = content

    class MockLLM:
        def invoke(self, prompt):
            return MockResponse(
                '```json\n'
                '{\n'
                '  "retrieved_relevance": [true, false],\n'
                '  "candidate_relevance": [true, false],\n'
                '  "faithfulness": 0.85,\n'
                '  "answer_relevancy": 0.95,\n'
                '  "context_recall": 0.75\n'
                '}\n'
                '```'
            )

    class MockLLMClient:
        def __init__(self):
            self.llm = MockLLM()

    result = unified_deep_evaluation(
        query="test query",
        answer="test answer",
        retrieved_chunks=["chunk 1", "chunk 2"],
        candidate_chunks=["chunk 1", "chunk 2"],
        llm_client=MockLLMClient()
    )

    assert result["retrieved_flags"] == [True, False]
    assert result["faithfulness"] == 0.85


@pytest.mark.anyio
async def test_build_message_evaluation_report_raises_429(async_db_session, user_a, sample_config_and_chat, monkeypatch):
    cfg, msg = sample_config_and_chat

    # Insert a user query so that we have an associated user message
    user_msg = ChatMessage(
        user_id=user_a.id,
        document_id=msg.document_id,
        config_id=cfg.id,
        role="user",
        content="hello query",
        timestamp=msg.timestamp - datetime.timedelta(seconds=5)
    )
    async_db_session.add(user_msg)
    await async_db_session.commit()

    # Mock PipelineFactory.create_pipeline
    class MockPipeline:
        def __init__(self):
            self.llm_client = "mock-client"
            self.embedder = "mock-embedder"
        async def aretrieve(self, query, top_k):
            return []

    monkeypatch.setattr(PipelineFactory, "create_pipeline", lambda cfg: MockPipeline())

    # Mock unified_deep_evaluation to raise a 429 error
    def mock_unified(*args, **kwargs):
        raise Exception("RESOURCE_EXHAUSTED: Quota exceeded limit 20")

    monkeypatch.setattr("app.api.evaluation.unified_deep_evaluation", mock_unified)

    with pytest.raises(EvaluationServiceUnavailableError) as exc_info:
        await build_message_evaluation_report(
            db=async_db_session,
            message_id=msg.id,
            user_id=user_a.id,
            deep=True
        )

    assert "quota limit exceeded" in str(exc_info.value)


@pytest.mark.anyio
async def test_evaluate_faithfulness_alias_injects_current_user(async_db_session, user_a, sample_config_and_chat, monkeypatch):
    import httpx
    from fastapi import FastAPI
    from app.api.evaluation import router as evaluation_router
    from app.auth import get_current_user
    from app.database import get_db
    from app.models.evaluation import EvaluationResult

    cfg, msg = sample_config_and_chat

    user_msg = ChatMessage(
        user_id=user_a.id,
        document_id=msg.document_id,
        config_id=cfg.id,
        role="user",
        content="What is the deadline?",
        timestamp=msg.timestamp - datetime.timedelta(seconds=5),
    )
    async_db_session.add(user_msg)
    await async_db_session.commit()

    class MockPipeline:
        llm_client = None

    monkeypatch.setattr(PipelineFactory, "create_pipeline", lambda cfg_json: MockPipeline())

    def fake_score_message(db, assistant_msg, query_text, llm_client, chunks):
        res = EvaluationResult(
            message_id=assistant_msg.id,
            faithfulness=0.91,
            answer_relevancy=0.88,
            context_precision=0.8,
            context_recall=0.75,
        )
        db.add(res)
        return res

    monkeypatch.setattr("app.api.evaluation.score_message", fake_score_message)

    test_app = FastAPI()
    test_app.include_router(evaluation_router)
    test_app.dependency_overrides[get_db] = lambda: async_db_session
    test_app.dependency_overrides[get_current_user] = lambda: user_a

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as client:
        resp = await client.post("/api/evaluation/faithfulness", json={"message_id": str(msg.id)})

    assert resp.status_code == 200
    body = resp.json()
    assert body["message_id"] == str(msg.id)
    assert body["faithfulness"] == 0.91
    assert body["answer_relevancy"] == 0.88
    assert body["context_precision"] == 0.8
    assert body["context_recall"] == 0.75


def test_evaluate_faithfulness_alias_requires_auth():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.evaluation import router as evaluation_router

    test_app = FastAPI()
    test_app.include_router(evaluation_router)

    with TestClient(test_app) as client:
        resp = client.post("/api/evaluation/faithfulness", json={"message_id": "00000000-0000-0000-0000-000000000001"})

    assert resp.status_code == 401


@pytest.mark.anyio
async def test_score_message_does_not_persist_all_none_result(async_db_session, sample_config_and_chat, monkeypatch):
    from types import SimpleNamespace
    from sqlalchemy import select
    from app.api.evaluation import score_message
    from app.models.evaluation import EvaluationResult

    _, msg = sample_config_and_chat

    monkeypatch.setattr(FaithfulnessEvaluator, "evaluate", lambda *a, **kw: None)
    monkeypatch.setattr(AnswerRelevancyEvaluator, "evaluate", lambda *a, **kw: None)
    monkeypatch.setattr(ContextQualityEvaluator, "evaluate", lambda *a, **kw: {})

    fake_llm = SimpleNamespace(llm=object())
    with pytest.raises(EvaluationServiceUnavailableError):
        score_message(
            db=async_db_session,
            assistant_msg=msg,
            query_text="What is this about?",
            llm_client=fake_llm,
            chunks=[],
        )

    rows = (
        await async_db_session.execute(
            select(EvaluationResult).where(EvaluationResult.message_id == msg.id)
        )
    ).scalars().all()
    assert rows == []


@pytest.mark.anyio
async def test_score_message_by_id_rejects_degraded_fallback_answer(async_db_session, user_a, sample_config_and_chat):
    from app.api.evaluation import EvaluationBadRequestError, score_message_by_id

    cfg, msg = sample_config_and_chat
    msg.content = "LLM is temporarily unavailable, so this answer is based directly on retrieved chunks.\nQuestion: hi"
    user_msg = ChatMessage(
        user_id=user_a.id,
        document_id=msg.document_id,
        config_id=cfg.id,
        role="user",
        content="hi",
        timestamp=msg.timestamp - datetime.timedelta(seconds=5),
    )
    async_db_session.add(user_msg)
    await async_db_session.commit()

    with pytest.raises(EvaluationBadRequestError) as exc_info:
        await score_message_by_id(db=async_db_session, message_id=msg.id, user_id=user_a.id)
    assert exc_info.value.status_code == 400


@pytest.mark.anyio
async def test_chat_endpoint_skips_scoring_on_llm_fallback_and_marks_degraded(
    async_db_session, user_a, sample_config_and_chat, monkeypatch
):
    from types import SimpleNamespace
    from app.api.chat import chat_endpoint
    from app.models.metrics import Metrics
    from app.services.pipeline_manager import PipelineManager

    Metrics.__table__.create(bind=async_db_session._sync.get_bind(), checkfirst=True)
    cfg, _ = sample_config_and_chat

    class _FakeLimiter:
        def build_scope_key(self, user_id):
            return f"user:{user_id}"

        async def enforce_rate_limit(self, scope_key, op):
            return None

        async def record_call(self, scope_key, op, user_id):
            return None

    class _FailingPipeline:
        llm_client = SimpleNamespace(llm=object())

        async def aretrieve(self, query, top_k=5):
            return [(Chunk(id="c1", text="Relevant fact in document.", metadata={}), 0.85)]

        async def agenerate(self, query, chunks):
            raise RuntimeError("upstream LLM timeout")

    score_calls = []
    monkeypatch.setattr("app.api.chat.classify_query", lambda _q: "local")
    monkeypatch.setattr(PipelineManager, "get_pipeline", classmethod(lambda cls, k, c: _FailingPipeline()))
    monkeypatch.setattr("app.api.evaluation.score_message", lambda **kw: score_calls.append(kw))

    resp = await chat_endpoint(
        query="What is the relevant fact?",
        doc_id=cfg.document_id,
        config_id=cfg.id,
        current_user=user_a,
        db=async_db_session,
        rate_limiter=_FakeLimiter(),
    )
    assert resp["degraded"] is True
    assert "LLM is temporarily unavailable" in resp["answer"]
    assert score_calls == []




