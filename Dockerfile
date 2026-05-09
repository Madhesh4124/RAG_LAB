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
COPY start.sh /app/backend/start.sh
RUN chmod +x /app/backend/start.sh

WORKDIR /app/backend

# P4.2: Run as a non-root user for security.
RUN addgroup --gid 1001 appgroup \
 && adduser --uid 1001 --gid 1001 --disabled-password --no-create-home --gecos "" appuser \
 && chown -R appuser:appgroup /app

USER appuser

# Ensure the app uses an on-disk DB location under /app so it's writable.
ENV CHROMA_PERSIST_DIR=/app/backend

# Use start script to prepare DB, run migrations, then start Gunicorn.
CMD ["/app/backend/start.sh"]
