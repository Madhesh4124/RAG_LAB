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
COPY backend/start.sh /app/backend/start.sh
RUN chmod +x /app/backend/start.sh

WORKDIR /app/backend

# P4.2: Run as non-root user with home and cache directories.
# Hugging Face Spaces defaults to UID 1000.
RUN useradd -m -u 1000 -s /bin/bash appuser \
 && mkdir -p /home/appuser/.cache /app/backend/chroma_db /app/backend/uploads \
 && chown -R appuser:appuser /home/appuser /app \
 && chmod -R 777 /home/appuser/.cache /tmp

USER appuser

ENV HOME=/home/appuser \
    HF_HOME=/home/appuser/.cache/huggingface \
    TRANSFORMERS_CACHE=/home/appuser/.cache/huggingface \
    TORCH_HOME=/home/appuser/.cache/torch \
    CHROMA_PERSIST_DIR=/app/backend/chroma_db

# Use start script to prepare DB, run migrations, then start Gunicorn.
CMD ["/bin/sh", "/app/backend/start.sh"]
