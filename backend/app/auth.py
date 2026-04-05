import os
import uuid
from datetime import timedelta, datetime, timezone

import bcrypt
from fastapi import Depends, HTTPException, Request, Response, status
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, PasswordResetToken

SESSION_COOKIE_NAME = "raglab_session"
SESSION_MAX_AGE_SECONDS = int(timedelta(days=7).total_seconds())
PASSWORD_RESET_TOKEN_EXPIRY_MINUTES = 30


def _get_serializer() -> URLSafeTimedSerializer:
    secret = os.getenv("AUTH_SECRET_KEY")
    if not secret:
        # Generate a default secret if not provided (not secure for production, but safe for HF Spaces dev)
        import hashlib
        secret = hashlib.sha256(b"raglab-default-secret").hexdigest()
        print("[WARNING] AUTH_SECRET_KEY not set. Using default. Set AUTH_SECRET_KEY in environment for production.")
    return URLSafeTimedSerializer(secret_key=secret, salt="raglab-auth")


def _get_reset_serializer() -> URLSafeTimedSerializer:
    secret = os.getenv("AUTH_SECRET_KEY")
    if not secret:
        # Generate a default secret if not provided (not secure for production, but safe for HF Spaces dev)
        import hashlib
        secret = hashlib.sha256(b"raglab-default-secret").hexdigest()
    return URLSafeTimedSerializer(secret_key=secret, salt="raglab-password-reset")


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


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=False,
        samesite="lax",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, httponly=True, samesite="lax")


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        user_id = decode_session_token(token)
    except BadSignature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
