# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install build tools needed for native extensions (e.g. rank-bm25, tokenizers)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual-env so the runtime stage gets a clean, isolated install.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/requirements.txt /build/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r /build/requirements.txt


# ── Stage 2: minimal runtime ──────────────────────────────────────────────────
FROM python:3.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy only the virtualenv and application source — no build tools.
COPY --from=builder /opt/venv /opt/venv
COPY backend /app/backend

WORKDIR /app/backend

# P4.2: Run as a non-root user for security.
RUN addgroup --gid 1001 appgroup \
 && adduser --uid 1001 --gid 1001 --disabled-password --no-create-home appuser \
 && chown -R appuser:appgroup /app

USER appuser

# Hugging Face Spaces Docker runtime exposes PORT (default 7860).
CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w ${WEB_CONCURRENCY:-4} --bind 0.0.0.0:${PORT:-7860} --timeout ${GUNICORN_TIMEOUT:-120} --log-level ${LOG_LEVEL:-info} --access-logfile - --error-logfile - --capture-output"]
