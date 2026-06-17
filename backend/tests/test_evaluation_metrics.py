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


