import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base, SessionLocal
from app.bootstrap_migrations import run_bootstrap_migrations
from app.models.user import User  # noqa: F401 - imported so SQLAlchemy registers table metadata
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.documents import router as documents_router
from app.api.chat import router as chat_router
from app.api.config import router as config_router
from app.api.analysis import router as analysis_router
from app.api.compare import router as compare_router
from app.api.evaluation import router as evaluation_router
from app.api.metrics import router as metrics_router
from app.compare.router import router as compare_module_router

# Suppress noisy Chroma telemetry errors (version mismatch with posthog)
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        run_bootstrap_migrations(engine, db)
    finally:
        db.close()

    # Startup event to notify users logging cleanly
    logger.info("RAG Lab API is ready")
    print("RAG Lab API is ready")  # explicit local console signal
    yield

# Create FastAPI app instance
app = FastAPI(title="RAG Lab API", lifespan=lifespan)

# Configure CORS Middleware allowing local frontend testing smoothly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all API specific routers directly
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(config_router)
app.include_router(analysis_router)
app.include_router(compare_router)
app.include_router(evaluation_router)
app.include_router(metrics_router)
app.include_router(compare_module_router)

# Define root health check purely optionally
@app.get("/")
def root():
    return {"status": "RAG Lab API backend is online"}

@app.get("/health")
def health():
    return {"status": "ok"}
