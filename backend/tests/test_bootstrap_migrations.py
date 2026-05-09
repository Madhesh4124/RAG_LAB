from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.bootstrap_migrations import run_bootstrap_migrations
from app.database import Base
from app.models.chat import ChatMessage
from app.models.document import Document
from app.models.rag_config import RAGConfig
from app.models.user import User


@pytest.mark.anyio
async def test_bootstrap_migrations_create_evaluation_results_table(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-secret")
    monkeypatch.setenv("AUTH_SEED_PASSWORD", "change-me")

    db_path = tmp_path / "bootstrap_eval.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: Base.metadata.create_all(
                    bind=sync_conn,
                    tables=[
                        User.__table__,
                        Document.__table__,
                        RAGConfig.__table__,
                        ChatMessage.__table__,
                    ],
                )
            )

        async with session_factory() as db:
            await run_bootstrap_migrations(engine, db)

        async with engine.begin() as conn:
            has_table = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).has_table("evaluation_results")
            )

        assert has_table is True
    finally:
        await engine.dispose()
