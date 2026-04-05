from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth import (
    clear_auth_cookie, create_session_token, get_current_user, hash_password,
    set_auth_cookie, verify_password, create_password_reset_token,
    decode_password_reset_token
)
from app.database import get_db
from app.models.user import (
    User, UserLoginRequest, UserResponse, UserSignupRequest,
    PasswordResetRequestBody, PasswordResetConfirmBody, PasswordResetResponse
)
from app.services.email_service import EmailService
from itsdangerous import BadSignature

router = APIRouter(prefix="/api/auth", tags=["auth"])
email_service = EmailService()


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: UserSignupRequest, response: Response, db: Session = Depends(get_db)):
    stmt = select(User).where(or_(User.username == payload.username, User.email == payload.email))
    existing = db.execute(stmt).scalars().first()
    if existing:
        raise HTTPException(status_code=409, detail="Username or email already in use")

    user = User(
        username=payload.username.strip(),
        email=payload.email.strip().lower(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_session_token(user.id)
    set_auth_cookie(response, token)
    return user


@router.post("/login", response_model=UserResponse)
def login(payload: UserLoginRequest, response: Response, db: Session = Depends(get_db)):
    identifier = payload.identifier.strip()
    stmt = select(User).where(or_(User.username == identifier, User.email == identifier.lower()))
    user = db.execute(stmt).scalars().first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_session_token(user.id)
    set_auth_cookie(response, token)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    clear_auth_cookie(response)
    return None


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/password-reset/request", status_code=status.HTTP_200_OK)
def request_password_reset(
    payload: PasswordResetRequestBody,
    db: Session = Depends(get_db),
):
    """Request a password reset email. Always returns success for security."""
    stmt = select(User).where(User.email == payload.email.lower())
    user = db.execute(stmt).scalars().first()

    if user:
        reset_token = create_password_reset_token(user.id)
        email_service.send_password_reset_email(user.email, reset_token)

    # Always return success to prevent email enumeration attacks
    return PasswordResetResponse(
        success=True,
        message="If an account exists with this email, a password reset link has been sent."
    )


@router.post("/password-reset/confirm", response_model=PasswordResetResponse)
def confirm_password_reset(
    payload: PasswordResetConfirmBody,
    db: Session = Depends(get_db),
):
    """Confirm password reset with token and new password."""
    try:
        user_id = decode_password_reset_token(payload.token)
    except BadSignature:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(payload.new_password)
    from datetime import datetime, timezone
    user.password_reset_count = datetime.now(timezone.utc)
    db.commit()

    return PasswordResetResponse(
        success=True,
        message="Password has been reset successfully. Please login with your new password."
    )


@router.post("/password-change", status_code=status.HTTP_200_OK)
def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change password for authenticated user."""
    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    current_user.password_hash = hash_password(new_password)
    from datetime import datetime, timezone
    current_user.password_reset_count = datetime.now(timezone.utc)
    db.commit()

    return {"success": True, "message": "Password changed successfully"}
