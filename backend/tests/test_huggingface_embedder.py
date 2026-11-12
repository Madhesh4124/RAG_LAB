import threading
from app.services.embedding import huggingface_api_embedder as hf_mod
from app.services.embedding.huggingface_api_embedder import HuggingFaceAPIEmbedder


class _FakeLocalEmbeddings:
    def __init__(self):
        self.query_calls = 0
        self.doc_calls = 0

    def embed_query(self, text: str):
        self.query_calls += 1
        return [0.1, 0.2]

    def embed_documents(self, texts: list[str]):
        self.doc_calls += 1
        return [[0.1, 0.2] for _ in texts]


def test_hf_embedder_recovers_after_transient_cooldown(monkeypatch):
    fake_now = {"t": 100.0}
    monkeypatch.setattr(hf_mod.time, "monotonic", lambda: fake_now["t"])
    monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)

    embedder = HuggingFaceAPIEmbedder(cooldown_seconds=30.0)
    local = _FakeLocalEmbeddings()
    embedder._local_embeddings = local

    remote_calls = {"n": 0, "fail": True}

    class _FakeRemote:
        def embed_query(self, text: str):
            remote_calls["n"] += 1
            if remote_calls["fail"]:
                raise RuntimeError("503 Service Unavailable")
            return [0.9, 0.8]

        def embed_documents(self, texts: list[str]):
            remote_calls["n"] += 1
            return [[0.9, 0.8] for _ in texts]

    embedder._remote_embeddings = _FakeRemote()
    embedder._circuit_state = "closed"

    # 1. Transient failure opens circuit and falls back to local
    assert embedder.embed_text("hello") == [0.1, 0.2]
    assert embedder._circuit_state == "open"
    assert remote_calls["n"] == 1
    assert local.query_calls == 1

    # 2. During cooldown window, remote is skipped cleanly
    fake_now["t"] = 110.0
    assert embedder.embed_text("still cooling down") == [0.1, 0.2]
    assert remote_calls["n"] == 1
    assert local.query_calls == 2

    # 3. After cooldown expires, half-open probe succeeds and closes circuit
    fake_now["t"] = 131.0
    remote_calls["fail"] = False
    assert embedder.embed_text("recovered") == [0.9, 0.8]
    assert embedder._circuit_state == "closed"
    assert remote_calls["n"] == 2
    assert embedder.embed_batch(["a", "b"]) == [[0.9, 0.8], [0.9, 0.8]]
    assert remote_calls["n"] == 3


def test_hf_embedder_permanent_error_stays_open_after_cooldown(monkeypatch):
    fake_now = {"t": 100.0}
    monkeypatch.setattr(hf_mod.time, "monotonic", lambda: fake_now["t"])
    monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)

    embedder = HuggingFaceAPIEmbedder(cooldown_seconds=10.0)
    local = _FakeLocalEmbeddings()
    embedder._local_embeddings = local

    remote_calls = {"n": 0}

    class _PaymentErrRemote:
        def embed_documents(self, texts: list[str]):
            remote_calls["n"] += 1
            raise RuntimeError("402 Payment Required: inference credits exhausted")

    embedder._remote_embeddings = _PaymentErrRemote()
    embedder._circuit_state = "closed"

    assert embedder.embed_batch(["hello"]) == [[0.1, 0.2]]
    assert embedder._circuit_state == "permanently_open"
    assert embedder._remote_embeddings is None

    fake_now["t"] = 9999.0
    assert embedder.embed_batch(["after long time"]) == [[0.1, 0.2]]
    assert remote_calls["n"] == 1
    assert local.doc_calls == 2


def test_hf_embedder_half_open_prevents_thundering_herd(monkeypatch):
    fake_now = {"t": 100.0}
    monkeypatch.setattr(hf_mod.time, "monotonic", lambda: fake_now["t"])
    monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)

    embedder = HuggingFaceAPIEmbedder(cooldown_seconds=10.0)
    local = _FakeLocalEmbeddings()
    embedder._local_embeddings = local

    entered_probe = threading.Event()
    release_probe = threading.Event()
    probe_calls = {"n": 0}

    class _SlowProbeRemote:
        def embed_query(self, text: str):
            probe_calls["n"] += 1
            entered_probe.set()
            release_probe.wait(timeout=2.0)
            return [0.7, 0.7]

    embedder._remote_embeddings = _SlowProbeRemote()
    embedder._circuit_state = "open"
    embedder._cooldown_until = 95.0  # Ready to probe

    results = []
    t1 = threading.Thread(target=lambda: results.append(embedder.embed_text("probe")))
    t1.start()
    assert entered_probe.wait(timeout=2.0)

    # Concurrent caller while probe is running must not also hit remote.
    concurrent_res = embedder.embed_text("concurrent")
    assert concurrent_res == [0.1, 0.2]
    assert probe_calls["n"] == 1

    release_probe.set()
    t1.join(timeout=2.0)
    assert results == [[0.7, 0.7]]
    assert embedder._circuit_state == "closed"
