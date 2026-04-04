import os
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import Column, DateTime, String, Uuid

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    @property
    def is_admin(self) -> bool:
        seed_username = os.getenv("AUTH_SEED_USERNAME", "admin")
        seed_email = os.getenv("AUTH_SEED_EMAIL", "admin@local")
        return self.username == seed_username or self.email == seed_email


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
