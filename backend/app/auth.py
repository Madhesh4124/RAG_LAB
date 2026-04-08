import os
import uuid
from datetime import timedelta, datetime, timezone
import hashlib

import bcrypt
from fastapi import Depends, HTTPException, Request, Response, status
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, get_db
from app.models.user import User, PasswordResetToken

SESSION_COOKIE_NAME = "raglab_session"
SESSION_MAX_AGE_SECONDS = int(timedelta(days=7).total_seconds())
PASSWORD_RESET_TOKEN_EXPIRY_MINUTES = 30


def _auth_secret() -> str:
    secret = os.getenv("AUTH_SECRET_KEY")
    if secret:
        return secret

    allow_insecure = os.getenv("ALLOW_INSECURE_AUTH_SECRET", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if allow_insecure:
        return hashlib.sha256(b"raglab-default-secret").hexdigest()

    raise RuntimeError(
        "AUTH_SECRET_KEY is required. Set AUTH_SECRET_KEY in environment "
        "(or set ALLOW_INSECURE_AUTH_SECRET=true for local-only development)."
    )


_AUTH_SECRET = _auth_secret()


def _get_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key=_AUTH_SECRET, salt="raglab-auth")


def _get_reset_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key=_AUTH_SECRET, salt="raglab-password-reset")


def hash_password(raw_password: str) -> str:
    hashed = bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(raw_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(raw_password.encode("utf-8"), password_hash.encode("utf-8"))


def create_session_token(user_id: uuid.UUID) -> str:
    serializer = _get_serializer()
    return serializer.dumps({"user_id": str(user_id)})


def decode_session_token(token: str) -> uuid.UUID:
    serializer = _get_serializer()
    payload = serializer.loads(token, max_age=SESSION_MAX_AGE_SECONDS)
    try:
        return uuid.UUID(payload["user_id"])
    except Exception as exc:
        raise BadSignature("Invalid token payload") from exc


def create_password_reset_token(user_id: uuid.UUID) -> str:
    """Create a password reset token."""
    serializer = _get_reset_serializer()
    return serializer.dumps({"user_id": str(user_id)})


def decode_password_reset_token(token: str) -> uuid.UUID:
    """Decode and verify password reset token."""
    serializer = _get_reset_serializer()
    max_age_seconds = PASSWORD_RESET_TOKEN_EXPIRY_MINUTES * 60
    payload = serializer.loads(token, max_age=max_age_seconds)
    try:
        return uuid.UUID(payload["user_id"])
    except Exception as exc:
        raise BadSignature("Invalid or expired reset token") from exc


def _cookie_settings() -> tuple[bool, str]:
    """Return secure/samesite values compatible with local and deployed frontends."""
    cookie_secure = os.getenv("COOKIE_SECURE")
    cookie_samesite = os.getenv("COOKIE_SAMESITE")

    if cookie_secure is None:
        # Default to secure cookies in deployments (HF Spaces / Vercel).
        cookie_secure_bool = True
    else:
        cookie_secure_bool = cookie_secure.lower() != "false"

    if cookie_samesite is None:
        # Cross-site frontend->backend calls require SameSite=None.
        cookie_samesite_value = "none" if cookie_secure_bool else "lax"
    else:
        cookie_samesite_value = cookie_samesite.lower()

    return cookie_secure_bool, cookie_samesite_value


def set_auth_cookie(response: Response, token: str) -> None:
    use_secure, same_site = _cookie_settings()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=use_secure,
        samesite=same_site,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    use_secure, same_site = _cookie_settings()
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=use_secure,
        samesite=same_site,
        path="/",
    )


async def get_current_user(request: Request) -> User:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        user_id = decode_session_token(token)
    except BadSignature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    async with AsyncSessionLocal() as db:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
