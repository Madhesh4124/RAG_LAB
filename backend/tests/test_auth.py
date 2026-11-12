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


@pytest.mark.anyio
async def test_password_reset_token_is_single_use_and_respects_cooldown(async_db_session, user_a, monkeypatch):
    from datetime import datetime, timedelta, timezone
    import httpx
    from fastapi import FastAPI
    from sqlalchemy import select
    from app.api.auth import email_service, router as auth_router
    from app.database import get_db
    from app.models.user import PasswordResetToken

    monkeypatch.setenv("AUTH_SECRET_KEY", "test-secret")
    monkeypatch.setenv("PASSWORD_RESET_COOLDOWN_SECONDS", "60")

    sent_tokens = []

    def fake_send_reset_email(email, reset_token, reset_url=None):
        sent_tokens.append(reset_token)

    monkeypatch.setattr(email_service, "send_password_reset_email", fake_send_reset_email)

    test_app = FastAPI()
    test_app.include_router(auth_router)
    test_app.dependency_overrides[get_db] = lambda: async_db_session

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as client:
        # 1. Request reset -> issues 1st token
        resp1 = await client.post("/api/auth/password-reset/request", json={"email": user_a.email})
        assert resp1.status_code == 200
        assert len(sent_tokens) == 1
        token1 = sent_tokens[0]

        # 2. Immediate second request is suppressed by cooldown (returns generic 200, sends no new email)
        resp2 = await client.post("/api/auth/password-reset/request", json={"email": user_a.email})
        assert resp2.status_code == 200
        assert len(sent_tokens) == 1

        # 3. Age the 1st token past cooldown and request again -> invalidates token1, issues token2
        rows = (await async_db_session.execute(select(PasswordResetToken))).scalars().all()
        assert len(rows) == 1
        rows[0].created_at = datetime.now(timezone.utc) - timedelta(seconds=120)
        await async_db_session.commit()

        resp3 = await client.post("/api/auth/password-reset/request", json={"email": user_a.email})
        assert resp3.status_code == 200
        assert len(sent_tokens) == 2
        token2 = sent_tokens[1]
        assert token2 != token1

        # 4. Old token1 must be rejected because token2 superseded it
        replay_old = await client.post(
            "/api/auth/password-reset/confirm",
            json={"token": token1, "new_password": "new-password-1"},
        )
        assert replay_old.status_code == 400

        # 5. Confirm with token2 succeeds once
        confirm_ok = await client.post(
            "/api/auth/password-reset/confirm",
            json={"token": token2, "new_password": "new-password-2"},
        )
        assert confirm_ok.status_code == 200
        assert verify_password("new-password-2", user_a.password_hash)

        # 6. Replaying token2 must fail
        replay_used = await client.post(
            "/api/auth/password-reset/confirm",
            json={"token": token2, "new_password": "new-password-3"},
        )
        assert replay_used.status_code == 400

        # 7. Request immediately after confirm is suppressed by user.password_reset_count cooldown
        resp4 = await client.post("/api/auth/password-reset/request", json={"email": user_a.email})
        assert resp4.status_code == 200
        assert len(sent_tokens) == 2


@pytest.mark.anyio
async def test_session_revoked_on_logout_and_password_reset(async_db_session, user_a, monkeypatch):
    import httpx
    from fastapi import FastAPI
    from app.api.auth import email_service, router as auth_router
    from app.database import get_db

    monkeypatch.setenv("AUTH_SECRET_KEY", "test-secret")
    monkeypatch.setenv("PASSWORD_RESET_COOLDOWN_SECONDS", "0")

    class _SessionContext:
        async def __aenter__(self):
            return async_db_session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.auth.AsyncSessionLocal", lambda: _SessionContext())

    user_a.password_hash = hash_password("initial-password")
    await async_db_session.commit()

    sent_tokens = []
    monkeypatch.setattr(
        email_service,
        "send_password_reset_email",
        lambda email, reset_token, reset_url=None: sent_tokens.append(reset_token),
    )

    test_app = FastAPI()
    test_app.include_router(auth_router)
    test_app.dependency_overrides[get_db] = lambda: async_db_session

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as client:
        # Login -> token1 works
        login_resp = await client.post(
            "/api/auth/login",
            json={"identifier": user_a.username, "password": "initial-password"},
        )
        assert login_resp.status_code == 200
        token1 = login_resp.json()["access_token"]

        me_ok = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token1}"})
        assert me_ok.status_code == 200

        # Logout revokes token1 even if presented as Bearer afterwards
        logout_resp = await client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token1}"})
        assert logout_resp.status_code == 204

        me_revoked = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token1}"})
        assert me_revoked.status_code == 401

        # Re-login -> token2 works, then password reset revokes token2
        login_resp2 = await client.post(
            "/api/auth/login",
            json={"identifier": user_a.username, "password": "initial-password"},
        )
        assert login_resp2.status_code == 200
        token2 = login_resp2.json()["access_token"]

        await client.post("/api/auth/password-reset/request", json={"email": user_a.email})
        reset_confirm = await client.post(
            "/api/auth/password-reset/confirm",
            json={"token": sent_tokens[-1], "new_password": "updated-password"},
        )
        assert reset_confirm.status_code == 200

        me_after_reset = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token2}"})
        assert me_after_reset.status_code == 401
