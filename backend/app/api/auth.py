from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth import clear_auth_cookie, create_session_token, get_current_user, hash_password, set_auth_cookie, verify_password
from app.database import get_db
from app.models.user import User, UserLoginRequest, UserResponse, UserSignupRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


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
