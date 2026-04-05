import os
import uuid

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.user import User


def _column_exists(engine: Engine, table_name: str, column_name: str) -> bool:
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    return any(col["name"] == column_name for col in columns)


def _add_user_id_column_if_missing(engine: Engine, table_name: str) -> None:
    if _column_exists(engine, table_name, "user_id"):
        return

    backend = engine.url.get_backend_name()
    if backend == "postgresql":
        ddl = f"ALTER TABLE {table_name} ADD COLUMN user_id UUID"
    else:
        # SQLite and others in local/dev setups.
        ddl = f"ALTER TABLE {table_name} ADD COLUMN user_id TEXT"

    with engine.begin() as conn:
        conn.execute(text(ddl))


def _add_password_reset_count_if_missing(engine: Engine) -> None:
    if _column_exists(engine, "users", "password_reset_count"):
        return

    backend = engine.url.get_backend_name()
    if backend == "postgresql":
        ddl = "ALTER TABLE users ADD COLUMN password_reset_count TIMESTAMP"
    else:
        # SQLite
        ddl = "ALTER TABLE users ADD COLUMN password_reset_count DATETIME"

    with engine.begin() as conn:
        conn.execute(text(ddl))


def _seed_admin_user(db: Session) -> User:
    username = os.getenv("AUTH_SEED_USERNAME", "admin")
    email = os.getenv("AUTH_SEED_EMAIL", "admin@local")

    user = db.query(User).filter(User.username == username).first()
    if user:
        return user

    # Import lazily to avoid circular imports.
    from app.auth import hash_password

    password = os.getenv("AUTH_SEED_PASSWORD", "change-me")
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _backfill_user_ids(db: Session, admin_user_id: uuid.UUID) -> None:
    uid = str(admin_user_id)

    db.execute(text("UPDATE documents SET user_id = :uid WHERE user_id IS NULL"), {"uid": uid})

    db.execute(
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

    db.execute(
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

    # Any orphan rows get assigned to seed admin to keep data reachable.
    db.execute(text("UPDATE rag_configs SET user_id = :uid WHERE user_id IS NULL"), {"uid": uid})
    db.execute(text("UPDATE chat_messages SET user_id = :uid WHERE user_id IS NULL"), {"uid": uid})
    db.commit()


def run_bootstrap_migrations(engine: Engine, db: Session) -> None:
    # Ensure ownership columns exist for pre-auth databases.
    for table in ("documents", "rag_configs", "chat_messages"):
        _add_user_id_column_if_missing(engine, table)

    # Add missing password_reset_count column if needed
    _add_password_reset_count_if_missing(engine)

    admin_user = _seed_admin_user(db)
    _backfill_user_ids(db, admin_user.id)
