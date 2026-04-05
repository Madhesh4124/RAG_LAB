from app.compare import collection_registry as registry
from app.services import pipeline_manager


class _FakeCollection:
    def count(self):
        return 1


class _FakeChroma:
    def __init__(self, collection_name, embedding_function, persist_directory):
        self.collection_name = collection_name
        self.embedding_function = embedding_function
        self.persist_directory = persist_directory
        self._collection = _FakeCollection()


def test_compare_registry_is_user_scoped(monkeypatch):
    registry.clear_collection_registry()
    monkeypatch.setattr(registry, "Chroma", _FakeChroma)

    a = registry.get_or_load_collection(
        collection_name="shared_cfg",
        embedding_provider="nvidia",
        embedding_model="nvidia/nv-embed-v1",
        user_scope="user-a",
    )
    b = registry.get_or_load_collection(
        collection_name="shared_cfg",
        embedding_provider="nvidia",
        embedding_model="nvidia/nv-embed-v1",
        user_scope="user-b",
    )

    assert a is not b
    assert a.collection_name.startswith("user_user-a_")
    assert b.collection_name.startswith("user_user-b_")


def test_pipeline_manager_cache_key_is_user_scoped(monkeypatch):
    pipeline_manager.PipelineManager.clear_cache()

    class _DummyPipeline:
        pass

    monkeypatch.setattr(
        pipeline_manager.PipelineFactory,
        "create_pipeline",
        lambda cfg: _DummyPipeline(),
    )

    p1 = pipeline_manager.PipelineManager.get_pipeline("user-a:cfg-1", {"x": 1})
    p2 = pipeline_manager.PipelineManager.get_pipeline("user-b:cfg-1", {"x": 1})
    p1_again = pipeline_manager.PipelineManager.get_pipeline("user-a:cfg-1", {"x": 1})

    assert p1 is not p2
    # Stateless manager now creates a fresh pipeline on every call.
    assert p1 is not p1_again
