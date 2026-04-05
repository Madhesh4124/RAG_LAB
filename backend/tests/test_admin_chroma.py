import pytest
from fastapi import HTTPException

from app.api.admin import _is_admin_user, list_chroma_roots, require_admin
from app.models.user import User


class _FakeCollection:
    def __init__(self, name: str):
        self.name = name
        self.metadata = {"scope": "test"}

    def count(self):
        return 1

    def get(self, limit=3, include=None):
        return {
            "ids": ["chunk-1"],
            "documents": ["sample document text"],
            "metadatas": [{"filename": "sample.txt"}],
        }


class _FakeClient:
    def __init__(self, path: str):
        self.path = path

    def list_collections(self):
        return [_FakeCollection("demo-collection")]

    def get_collection(self, name: str):
        return _FakeCollection(name)

    def delete_collection(self, name: str):
        self.deleted = name


def _make_user(username: str = "user_a", email: str = "user_a@example.com") -> User:
    return User(username=username, email=email, password_hash="hash")


def test_admin_user_flag_uses_seed_identity(monkeypatch):
    monkeypatch.setenv("AUTH_SEED_USERNAME", "admin")
    monkeypatch.setenv("AUTH_SEED_EMAIL", "admin@local")

    admin_user = _make_user(username="admin", email="admin@local")
    normal_user = _make_user()

    assert _is_admin_user(admin_user) is True
    assert _is_admin_user(normal_user) is False


def test_require_admin_rejects_non_admin(monkeypatch):
    monkeypatch.setenv("AUTH_SEED_USERNAME", "admin")
    monkeypatch.setenv("AUTH_SEED_EMAIL", "admin@local")

    with pytest.raises(HTTPException) as exc:
        require_admin(current_user=_make_user())

    assert exc.value.status_code == 403


@pytest.mark.anyio
async def test_list_chroma_roots_returns_collection_details(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_SEED_USERNAME", "admin")
    monkeypatch.setenv("AUTH_SEED_EMAIL", "admin@local")
    monkeypatch.setattr("app.api.admin.PersistentClient", _FakeClient)
    monkeypatch.setattr("app.api.admin._storage_roots", lambda: [tmp_path])

    response = await list_chroma_roots(current_user=_make_user(username="admin", email="admin@local"))

    assert len(response) == 1
    assert response[0].root_path == str(tmp_path)
    assert response[0].collections[0].name == "demo-collection"
    assert response[0].collections[0].count == 1