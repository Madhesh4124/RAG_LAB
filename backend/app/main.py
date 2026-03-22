import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.api.documents import router as documents_router
from app.api.chat import router as chat_router
from app.api.config import router as config_router
from app.api.analysis import router as analysis_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Database tables (using engine config from database.py)
logger.info("Initializing database tables...")
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup event to notify users logging cleanly
    logger.info("RAG Lab API is ready")
    print("RAG Lab API is ready")  # explicit local console signal
    yield

# Create FastAPI app instance
app = FastAPI(title="RAG Lab API", lifespan=lifespan)

# Configure CORS Middleware allowing local frontend testing smoothly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all API specific routers directly
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(config_router)
app.include_router(analysis_router)

# Define root health check purely optionally
@app.get("/")
def root():
    return {"status": "RAG Lab API backend is online"}

@app.get("/health")
def health():
    return {"status": "ok"}
