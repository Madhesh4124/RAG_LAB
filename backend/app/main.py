import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timezone

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
from app.services.rate_limiter import get_rate_limiter
from app.services.email_service import EmailService

# Suppress noisy Chroma telemetry errors (version mismatch with posthog)
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

email_service = EmailService()
rate_limiter = get_rate_limiter()


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


def _cors_origins() -> list[str]:
    origins = {
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    }
    frontend_url = os.getenv("FRONTEND_URL")
    if frontend_url:
        origins.add(frontend_url.rstrip("/"))
    return sorted(origins)


# Add global exception handler for 429 rate limit errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch API errors and send alerts for 429 rate limit errors."""
    error_str = str(exc).upper()
    
    # Check for 429 or rate limit errors
    is_rate_limit_error = (
        "429" in error_str or 
        "RESOURCE_EXHAUSTED" in error_str or 
        "RATE_LIMIT" in error_str or
        "TOO_MANY_REQUESTS" in error_str
    )
    
    if is_rate_limit_error:
        # Extract user info from request if authenticated
        user_email = "unknown"
        username = "unknown"
        
        try:
            from app.auth import decode_session_token
            from app.models.user import User
            from sqlalchemy import select
            
            token = request.cookies.get("raglab_session")
            if token:
                try:
                    user_id = decode_session_token(token)
                    db = SessionLocal()
                    stmt = select(User).where(User.id == user_id)
                    user = db.execute(stmt).scalars().first()
                    if user:
                        user_email = user.email
                        username = user.username
                    db.close()
                except:
                    pass
        except:
            pass
        
        # Send alert email to admin
        logger.warning(f"Rate limit error (429) for user {username} ({user_email})")
        email_service.send_rate_limit_alert(
            user_email=user_email,
            username=username,
            api_error="429 Too Many Requests",
            error_message=str(exc)
        )
        
        # Log the error event
        error_event = rate_limiter.record_rate_limit_error(
            user_id=None,
            call_type="api",
            error_message=str(exc)
        )
        logger.error(f"Rate limit event: {error_event}")

    # Re-raise or return error response
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An error occurred. Admin has been notified if this is a rate limit issue."}
    )


# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=r"https://([a-zA-Z0-9-]+\.)*(vercel\.app|hf\.space)",
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
