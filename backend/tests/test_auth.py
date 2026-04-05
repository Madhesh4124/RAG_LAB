import uuid

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.auth import (
    create_session_token,
    decode_session_token,
    get_current_user,
    hash_password,
    verify_password,
)


def _request_with_cookie(cookie_value: str) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"cookie", f"raglab_session={cookie_value}".encode("utf-8"))],
    }
    return Request(scope)


def test_password_hash_and_verify():
    raw = "super-secret"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed)
    assert not verify_password("wrong", hashed)


def test_session_token_roundtrip(monkeypatch):
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-secret")
    user_id = uuid.uuid4()
    token = create_session_token(user_id)
    decoded = decode_session_token(token)
    assert decoded == user_id


@pytest.mark.anyio
async def test_get_current_user_requires_cookie():
    req = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    with pytest.raises(HTTPException) as exc:
        await get_current_user(req)
    assert exc.value.status_code == 401


@pytest.mark.anyio
async def test_get_current_user_resolves_user(async_db_session, user_a, monkeypatch):
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-secret")

    class _SessionContext:
        async def __aenter__(self):
            return async_db_session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.auth.AsyncSessionLocal", lambda: _SessionContext())

    token = create_session_token(user_a.id)
    req = _request_with_cookie(token)
    current = await get_current_user(req)
    assert current.id == user_a.id
    assert current.username == "user_a"
