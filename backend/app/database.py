import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from .env, with smart defaults for HF Spaces
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Default to SQLite in /data for HF Spaces (mounted bucket)
    # Falls back to local SQLite if /data doesn't exist
    db_path = os.getenv("CHROMA_PERSIST_DIR", "/data")
    os.makedirs(db_path, exist_ok=True)
    DATABASE_URL = f"sqlite:///{db_path}/rag_lab.db"
    print(f"[INFO] DATABASE_URL not set. Using default: {DATABASE_URL}")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()

# FastAPI dependency for getting DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
