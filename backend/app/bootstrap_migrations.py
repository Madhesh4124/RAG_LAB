import os
import uuid

from sqlalchemy import inspect, select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession

from app.models.evaluation import EvaluationResult
from app.models.user import User


async def _column_exists(conn: AsyncConnection, table_name: str, column_name: str) -> bool:
    def _inspect(sync_conn):
        inspector = inspect(sync_conn)
        columns = inspector.get_columns(table_name)
        return any(col["name"] == column_name for col in columns)

    return await conn.run_sync(_inspect)


async def _table_exists(conn: AsyncConnection, table_name: str) -> bool:
    def _inspect(sync_conn):
        inspector = inspect(sync_conn)
        return inspector.has_table(table_name)

    return await conn.run_sync(_inspect)


async def _add_user_id_column_if_missing(conn: AsyncConnection, table_name: str) -> None:
    if await _column_exists(conn, table_name, "user_id"):
        return

    backend = conn.engine.url.get_backend_name()
    if backend == "postgresql":
        ddl = f"ALTER TABLE {table_name} ADD COLUMN user_id UUID"
    else:
        ddl = f"ALTER TABLE {table_name} ADD COLUMN user_id TEXT"

    await conn.execute(text(ddl))


async def _add_password_reset_count_if_missing(conn: AsyncConnection) -> None:
    if await _column_exists(conn, "users", "password_reset_count"):
        return

    backend = conn.engine.url.get_backend_name()
    if backend == "postgresql":
        ddl = "ALTER TABLE users ADD COLUMN password_reset_count TIMESTAMP"
    else:
        ddl = "ALTER TABLE users ADD COLUMN password_reset_count DATETIME"

    await conn.execute(text(ddl))


async def _add_is_admin_if_missing(conn: AsyncConnection) -> None:
    if await _column_exists(conn, "users", "is_admin"):
        return

    backend = conn.engine.url.get_backend_name()
    if backend == "postgresql":
        ddl = "ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE"
    else:
        ddl = "ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"

    await conn.execute(text(ddl))


async def _create_evaluation_results_table_if_missing(conn: AsyncConnection) -> None:
    if await _table_exists(conn, EvaluationResult.__tablename__):
        return

    await conn.run_sync(lambda sync_conn: EvaluationResult.__table__.create(sync_conn, checkfirst=True))


async def _seed_admin_user(db: AsyncSession) -> User:
    username = os.getenv("AUTH_SEED_USERNAME", "admin")
    email = os.getenv("AUTH_SEED_EMAIL", "admin@local")

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if user:
        if not user.is_admin:
            user.is_admin = True
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user

    from app.auth import hash_password

    password = os.getenv("AUTH_SEED_PASSWORD", "change-me")
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        is_admin=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _seed_sample_user(db: AsyncSession) -> User:
    username = os.getenv("AUTH_SAMPLE_USERNAME", "sample")
    email = os.getenv("AUTH_SAMPLE_EMAIL", "sample@local")

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if user:
        if user.is_admin:
            user.is_admin = False
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user

    from app.auth import hash_password

    password = os.getenv("AUTH_SAMPLE_PASSWORD", "sample")
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        is_admin=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _backfill_user_ids(db: AsyncSession, admin_user_id: uuid.UUID) -> None:
    uid = str(admin_user_id)

    await db.execute(text("UPDATE documents SET user_id = :uid WHERE user_id IS NULL"), {"uid": uid})

    await db.execute(
        text(
            """
            UPDATE rag_configs
            SET user_id = (
              SELECT d.user_id
              FROM documents d
              WHERE d.id = rag_configs.document_id
            )
            WHERE user_id IS NULL
            """
        )
    )

    await db.execute(
        text(
            """
            UPDATE chat_messages
            SET user_id = (
              SELECT rc.user_id
              FROM rag_configs rc
              WHERE rc.id = chat_messages.config_id
            )
            WHERE user_id IS NULL
            """
        )
    )

    await db.execute(text("UPDATE rag_configs SET user_id = :uid WHERE user_id IS NULL"), {"uid": uid})
    await db.execute(text("UPDATE chat_messages SET user_id = :uid WHERE user_id IS NULL"), {"uid": uid})
    await db.commit()


async def run_bootstrap_migrations(engine: AsyncEngine, db: AsyncSession) -> None:
    async with engine.begin() as conn:
        for table in ("documents", "rag_configs", "chat_messages"):
            await _add_user_id_column_if_missing(conn, table)

        await _add_password_reset_count_if_missing(conn)
        await _add_is_admin_if_missing(conn)
        await _create_evaluation_results_table_if_missing(conn)

    admin_user = await _seed_admin_user(db)
    await _seed_sample_user(db)
    await _backfill_user_ids(db, admin_user.id)
