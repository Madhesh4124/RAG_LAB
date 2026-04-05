import os

from dotenv import load_dotenv
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

# Load environment variables
load_dotenv()


def _resolve_database_url() -> str:
    """Return an async-compatible database URL."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        # Default to SQLite in /data for HF Spaces (mounted bucket)
        # Falls back to local SQLite if /data doesn't exist.
        db_path = os.getenv("CHROMA_PERSIST_DIR", "/data")
        os.makedirs(db_path, exist_ok=True)
        database_url = f"sqlite:///{db_path}/rag_lab.db"
        print(f"[INFO] DATABASE_URL not set. Using default: {database_url}")

    url = make_url(database_url)
    drivername = url.drivername.lower()

    if drivername.startswith("sqlite") and "+aiosqlite" not in drivername:
        return url.set(drivername="sqlite+aiosqlite").render_as_string(hide_password=False)

    if drivername.startswith("postgresql") and "+asyncpg" not in drivername:
        return url.set(drivername="postgresql+asyncpg").render_as_string(hide_password=False)

    return database_url


ASYNC_DATABASE_URL = _resolve_database_url()

# Create async SQLAlchemy engine and session factory.
engine = create_async_engine(ASYNC_DATABASE_URL, future=True)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)

# Create declarative base
Base = declarative_base()


async def get_db():
    """FastAPI dependency for getting an async DB session."""
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
