import os
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import Column, DateTime, String, Uuid, Boolean

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    password_reset_count = Column(DateTime, nullable=True)  # Track last password reset for rate limiting


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid(as_uuid=True), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)


class UserSignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLoginRequest(BaseModel):
    identifier: str
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    created_at: datetime
    is_admin: bool = False

    model_config = ConfigDict(from_attributes=True)


class PasswordResetRequestBody(BaseModel):
    email: EmailStr


class PasswordResetConfirmBody(BaseModel):
    token: str
    new_password: str


class PasswordResetResponse(BaseModel):
    success: bool
    message: str
