import logging
import os
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.background import BackgroundTask
from itsdangerous import BadSignature
from sqlalchemy import select

from app.database import engine, Base, AsyncSessionLocal
from app.bootstrap_migrations import run_bootstrap_migrations
from app.models.user import User  # noqa: F401 - imported so SQLAlchemy registers table metadata
from app.models.document_summary import DocumentSummary  # noqa: F401 - registers summary table metadata
from app.models.compare_summary import CompareSummary  # noqa: F401 - registers compare summary table metadata
from app.models.rate_limit import RateLimitEvent  # noqa: F401 - registers rate limit table metadata
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
from app.services.rate_limiter import DatabaseRateLimiter, RateLimitExceededException
from app.services.email_service import EmailService

# Suppress noisy Chroma telemetry errors (version mismatch with posthog)
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

# Configure logging
logging.basicConfig(level=logging.INFO)


class _JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, self.datefmt),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


if os.getenv("LOG_FORMAT", "text").strip().lower() == "json":
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.setFormatter(_JsonLogFormatter())

logger = logging.getLogger(__name__)


def _configure_third_party_logging() -> None:
    verbose_compare_logs = os.getenv("COMPARE_VERBOSE_LOGS", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if verbose_compare_logs:
        return

    # Reduce noisy informational logs from model/bootstrap internals.
    quiet_loggers = (
        "sentence_transformers",
        "transformers",
        "huggingface_hub",
        "httpx",
        "httpcore",
        "google_genai",
    )
    for name in quiet_loggers:
        logging.getLogger(name).setLevel(logging.WARNING)


_configure_third_party_logging()

email_service = EmailService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        await run_bootstrap_migrations(engine, db)

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


async def _resolve_request_user(request: Request) -> tuple[str, str]:
    """Best-effort extraction of request user identity for alerting."""
    user_email = "unknown"
    username = "unknown"

    token = request.cookies.get("raglab_session")
    if not token:
        return user_email, username

    try:
        from app.auth import decode_session_token

        user_id = decode_session_token(token)
    except (BadSignature, Exception):
        return user_email, username

    async with AsyncSessionLocal() as db:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        if user:
            return user.email, user.username
    return user_email, username


def _rate_limit_alert_task(user_email: str, username: str, error_message: str) -> None:
    email_service.send_rate_limit_alert(
        user_email=user_email,
        username=username,
        api_error="429 Too Many Requests",
        error_message=error_message,
    )


@app.exception_handler(RateLimitExceededException)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceededException):
    user_email, username = await _resolve_request_user(request)
    logger.warning("Rate limit exceeded for user %s (%s): %s", username, user_email, exc.message)

    error_event = DatabaseRateLimiter.record_rate_limit_error(
        scope_key=exc.scope_key,
        call_type=exc.call_type,
        error_message=exc.message,
    )
    logger.error("Rate limit event: %s", error_event)

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": exc.message},
        background=BackgroundTask(_rate_limit_alert_task, user_email, username, exc.message),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def global_exception_handler(_: Request, exc: Exception):
    logger.exception("Unhandled server exception: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected server error occurred."},
    )


# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=r"https://([a-zA-Z0-9-]+\.)*(vercel\.app|hf\.space)",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
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
