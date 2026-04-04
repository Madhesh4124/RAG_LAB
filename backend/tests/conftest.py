import os
import uuid
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import Base
from app.models.chat import ChatMessage
from app.models.document import Document
from app.models.rag_config import RAGConfig
from app.models.user import User


@pytest.fixture
def db_session(monkeypatch):
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-secret")

    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture
def user_a(db_session):
    user = User(
        username="user_a",
        email="user_a@example.com",
        password_hash="hash-a",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_b(db_session):
    user = User(
        username="user_b",
        email="user_b@example.com",
        password_hash="hash-b",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_docs(db_session, user_a, user_b):
    doc_a = Document(
        user_id=user_a.id,
        filename="alpha.txt",
        content="alpha content",
        file_type="txt",
        file_size=10,
    )
    doc_b = Document(
        user_id=user_b.id,
        filename="beta.txt",
        content="beta content",
        file_type="txt",
        file_size=10,
    )
    db_session.add_all([doc_a, doc_b])
    db_session.commit()
    db_session.refresh(doc_a)
    db_session.refresh(doc_b)
    return doc_a, doc_b


@pytest.fixture
def sample_config_and_chat(db_session, user_a, sample_docs):
    doc_a, _ = sample_docs
    cfg = RAGConfig(
        user_id=user_a.id,
        document_id=doc_a.id,
        name="cfg-a",
        config_json={"vectorstore": {"type": "chroma"}},
        is_active=True,
    )
    db_session.add(cfg)
    db_session.commit()
    db_session.refresh(cfg)

    msg = ChatMessage(
        user_id=user_a.id,
        document_id=doc_a.id,
        config_id=cfg.id,
        role="assistant",
        content="hello",
        retrieved_chunks=[],
    )
    db_session.add(msg)
    db_session.commit()
    db_session.refresh(msg)

    return cfg, msg
