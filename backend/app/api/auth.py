import logging
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, BackgroundTasks
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    PASSWORD_RESET_TOKEN_EXPIRY_MINUTES,
    clear_auth_cookie, create_session_token, decode_session_token, extract_session_token,
    get_current_user, hash_password, hash_reset_token, set_auth_cookie, verify_password,
    create_password_reset_token, decode_password_reset_token
)
from app.database import get_db
from app.models.user import (
    PasswordResetToken, User, UserLoginRequest, UserResponse, UserSignupRequest,
    PasswordResetRequestBody, PasswordResetConfirmBody, PasswordResetResponse
)
from app.services.email_service import EmailService
from itsdangerous import BadSignature

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])
email_service = EmailService()


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _reset_cooldown_seconds() -> int:
    try:
        return max(0, int(os.getenv("PASSWORD_RESET_COOLDOWN_SECONDS", "60")))
    except ValueError:
        return 60


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserSignupRequest, response: Response, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(or_(User.username == payload.username, User.email == payload.email))
    existing = (await db.execute(stmt)).scalars().first()
    if existing:
        raise HTTPException(status_code=409, detail="Username or email already in use")

    user = User(
        username=payload.username.strip(),
        email=payload.email.strip().lower(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_session_token(user.id, token_version=int(getattr(user, "token_version", 0) or 0))
    set_auth_cookie(response, token)
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at,
        is_admin=user.is_admin,
        access_token=token,
        token_type="bearer",
    )


@router.post("/login", response_model=UserResponse)
async def login(payload: UserLoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    identifier = payload.identifier.strip()
    stmt = select(User).where(or_(User.username == identifier, User.email == identifier.lower()))
    user = (await db.execute(stmt)).scalars().first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_session_token(user.id, token_version=int(getattr(user, "token_version", 0) or 0))
    set_auth_cookie(response, token)
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at,
        is_admin=user.is_admin,
        access_token=token,
        token_type="bearer",
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    raw_token = extract_session_token(request)
    if raw_token:
        try:
            user_id = decode_session_token(raw_token)
            user = (await db.execute(select(User).where(User.id == user_id))).scalars().first()
            if user is not None:
                user.token_version = int(getattr(user, "token_version", 0) or 0) + 1
                await db.commit()
        except Exception:
            pass
    clear_auth_cookie(response)
    return None


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/password-reset/request", status_code=status.HTTP_200_OK)
async def request_password_reset(
    payload: PasswordResetRequestBody,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Request a password reset email. Always returns success for security."""
    stmt = select(User).where(User.email == payload.email.lower())
    user = (await db.execute(stmt)).scalars().first()

    if user:
        now = datetime.now(timezone.utc)
        cooldown_seconds = _reset_cooldown_seconds()
        in_cooldown = False

        if cooldown_seconds > 0:
            last_reset_at = _as_utc(user.password_reset_count)
            if last_reset_at and (now - last_reset_at).total_seconds() < cooldown_seconds:
                in_cooldown = True
            else:
                latest_tok_stmt = (
                    select(PasswordResetToken)
                    .where(PasswordResetToken.user_id == user.id)
                    .order_by(PasswordResetToken.created_at.desc())
                    .limit(1)
                )
                latest_tok = (await db.execute(latest_tok_stmt)).scalars().first()
                latest_created = _as_utc(latest_tok.created_at) if latest_tok else None
                if latest_created and (now - latest_created).total_seconds() < cooldown_seconds:
                    in_cooldown = True

        if in_cooldown:
            logger.info("Password reset request suppressed by cooldown for user_id=%s", user.id)
        else:
            # Invalidate any prior unused reset tokens before issuing a new one.
            await db.execute(
                update(PasswordResetToken)
                .where(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.used_at.is_(None),
                )
                .values(used_at=now)
            )

            reset_token = create_password_reset_token(user.id)
            token_record = PasswordResetToken(
                user_id=user.id,
                token_hash=hash_reset_token(reset_token),
                created_at=now,
                expires_at=now + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRY_MINUTES),
                used_at=None,
            )
            db.add(token_record)
            await db.commit()

            # Resolve frontend base URL dynamically from request headers or environment
            origin = request.headers.get("origin")
            if not origin and request.headers.get("referer"):
                parsed = urlparse(request.headers.get("referer"))
                if parsed.scheme and parsed.netloc:
                    origin = f"{parsed.scheme}://{parsed.netloc}"

            env_frontend = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
            space_host = os.getenv("SPACE_HOST")
            hf_default = f"https://{space_host}" if space_host else None

            # Prefer non-localhost FRONTEND_URL if explicitly configured, else Origin header from caller
            if env_frontend and "localhost" not in env_frontend:
                base_url = env_frontend
            elif origin:
                base_url = origin.rstrip("/")
            elif env_frontend:
                base_url = env_frontend
            elif hf_default:
                base_url = hf_default
            else:
                base_url = "http://localhost:5173"

            reset_url = f"{base_url}/reset-password?token={reset_token}"
            background_tasks.add_task(email_service.send_password_reset_email, user.email, reset_token, reset_url=reset_url)

    # Always return success to prevent email enumeration attacks
    return PasswordResetResponse(
        success=True,
        message="If an account exists with this email, a password reset link has been sent."
    )


@router.post("/password-reset/confirm", response_model=PasswordResetResponse)
async def confirm_password_reset(
    payload: PasswordResetConfirmBody,
    db: AsyncSession = Depends(get_db),
):
    """Confirm password reset with single-use token and new password."""
    try:
        user_id = decode_password_reset_token(payload.token)
    except BadSignature:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    now = datetime.now(timezone.utc)
    token_hash = hash_reset_token(payload.token)
    tok_stmt = select(PasswordResetToken).where(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.user_id == user_id,
    )
    token_record = (await db.execute(tok_stmt)).scalars().first()
    if not token_record or token_record.used_at is not None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    expires_at = _as_utc(token_record.expires_at)
    if expires_at is None or expires_at < now:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token_record.used_at = now
    await db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.id != token_record.id,
        )
        .values(used_at=now)
    )

    user.password_hash = hash_password(payload.new_password)
    user.password_reset_count = now
    user.token_version = int(getattr(user, "token_version", 0) or 0) + 1
    await db.commit()

    return PasswordResetResponse(
        success=True,
        message="Password has been reset successfully. Please login with your new password."
    )


@router.post("/password-change", status_code=status.HTTP_200_OK)
async def change_password(
    old_password: str,
    new_password: str,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password for authenticated user."""
    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    db_user = (await db.execute(select(User).where(User.id == current_user.id))).scalars().first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(timezone.utc)
    db_user.password_hash = hash_password(new_password)
    db_user.password_reset_count = now
    next_version = int(getattr(db_user, "token_version", 0) or 0) + 1
    db_user.token_version = next_version
    await db.commit()

    new_token = create_session_token(current_user.id, token_version=next_version)
    set_auth_cookie(response, new_token)

    return {"success": True, "message": "Password changed successfully", "access_token": new_token}
