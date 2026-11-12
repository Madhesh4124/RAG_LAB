import math
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.best_preset import get_best_preset_config
from app.services.chunking.base import Chunk
from app.services.pipeline_factory import PipelineFactory
from app.services.retrieval.reranker import NvidiaReranker, get_reranker


def test_nvidia_reranker_sends_exact_payload_and_parses_logits(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key")
    reranker = NvidiaReranker()
    assert reranker.endpoint == "https://ai.api.nvidia.com/v1/retrieval/nvidia/nemotron-3.5-rerank-8b/reranking"
    assert reranker.model_name == "nvidia/nemotron-3.5-rerank-8b"

    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "rankings": [
                {"index": 1, "logit": -2.783203125},
                {"index": 0, "logit": -6.28125},
            ],
            "usage": {"prompt_tokens": 3651, "total_tokens": 3651},
        }
        return resp

    reranker.session.post = fake_post

    c0 = Chunk(id="c0", text="Biological DNA/RNA model")
    c1 = Chunk(
        id="c1",
        text="AI enables robots to perceive, plan, and act autonomously.",
        metadata={"image": "data:image/jpeg;base64,AAA"},
    )
    results = reranker.rerank(
        query="How is AI improving robotics?",
        results=[(c0, 0.80), (c1, 0.70)],
        top_k=2,
    )

    assert captured["url"] == "https://ai.api.nvidia.com/v1/retrieval/nvidia/nemotron-3.5-rerank-8b/reranking"
    assert captured["headers"]["Authorization"] == "Bearer nvapi-test-key"
    assert captured["json"] == {
        "model": "nvidia/nemotron-3.5-rerank-8b",
        "query": {"text": "How is AI improving robotics?"},
        "passages": [
            {"text": "Biological DNA/RNA model"},
            {
                "text": "AI enables robots to perceive, plan, and act autonomously.",
                "image": "data:image/jpeg;base64,AAA",
            },
        ],
    }

    assert [chunk.id for chunk, _ in results] == ["c1", "c0"]
    assert math.isclose(results[0][1], 1.0, rel_tol=1e-6)
    assert 0.0 < results[1][1] < results[0][1]


def test_nvidia_reranker_falls_back_gracefully_on_missing_key_or_error(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    reranker = NvidiaReranker()
    c0 = Chunk(id="c0", text="First")
    c1 = Chunk(id="c1", text="Second")

    fallback = reranker.rerank("query", [(c0, 0.9), (c1, 0.8)], top_k=1)
    assert len(fallback) == 1
    assert fallback[0][0].id == "c0"

    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key")
    reranker2 = NvidiaReranker()
    reranker2.session.post = MagicMock(side_effect=RuntimeError("503 upstream timeout"))
    fallback2 = reranker2.rerank("query", [(c0, 0.9), (c1, 0.8)], top_k=2)
    assert [c.id for c, _ in fallback2] == ["c0", "c1"]


def test_get_reranker_and_best_preset_use_nvidia_nemotron(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key")
    preset = get_best_preset_config()
    assert preset["retriever"]["reranker_provider"] == "nvidia"
    assert preset["retriever"]["reranker_model"] == "nvidia/nemotron-3.5-rerank-8b"

    rr = get_reranker(
        {
            "provider": "nvidia",
            "model": "nvidia/nemotron-3.5-rerank-8b",
        }
    )
    assert isinstance(rr, NvidiaReranker)
    assert rr.model_name == "nvidia/nemotron-3.5-rerank-8b"

    # PipelineFactory routes nvidia reranker configs cleanly without touching network
    monkeypatch.setattr(PipelineFactory, "create_llm_client", staticmethod(lambda cfg: None))
    monkeypatch.setattr(PipelineFactory, "create_embedder", staticmethod(lambda cfg: SimpleNamespace(model_name="stub")))
    monkeypatch.setattr(PipelineFactory, "create_chunker", staticmethod(lambda cfg, embedder=None: SimpleNamespace()))
    monkeypatch.setattr(PipelineFactory, "create_vectorstore", staticmethod(lambda cfg: SimpleNamespace(collection_name="col")))
    monkeypatch.setattr(PipelineFactory, "create_retriever", staticmethod(lambda cfg, vs, emb: SimpleNamespace()))

    pipeline = PipelineFactory.create_pipeline(preset)
    assert isinstance(pipeline.reranker, NvidiaReranker)
    assert pipeline.reranker.model_name == "nvidia/nemotron-3.5-rerank-8b"
