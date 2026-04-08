from app.services.vectorstore import chroma_store


class _FakeClient:
    def __init__(self, path, settings=None):
        self.path = path
        self.settings = settings


def test_cached_persistent_client_is_reused(monkeypatch, tmp_path):
    chroma_store._PERSISTENT_CLIENT_CACHE.clear()
    monkeypatch.setattr(chroma_store, "PersistentClient", _FakeClient)

    first = chroma_store._get_cached_persistent_client(str(tmp_path))
    second = chroma_store._get_cached_persistent_client(str(tmp_path))

    assert first is second
    assert first.path == str(tmp_path.resolve())
