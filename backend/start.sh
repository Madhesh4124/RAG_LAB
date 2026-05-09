#!/bin/sh
set -e

# Resolve a writable persist directory for SQLite/Chroma files.
FALLBACK_DB_DIR="/app/backend/chroma_data"
DB_DIR="${CHROMA_PERSIST_DIR:-$FALLBACK_DB_DIR}"

mkdir -p "$DB_DIR" || true

# On HF Spaces mounted volumes (for example /data), chown can be forbidden.
# Only try it as root, and never fail startup if ownership cannot be changed.
if [ "$(id -u)" -eq 0 ]; then
  chown -R appuser:appgroup "$DB_DIR" || echo "[WARN] Could not chown $DB_DIR, continuing"
fi

if [ ! -w "$DB_DIR" ]; then
  echo "[WARN] $DB_DIR is not writable by uid $(id -u). Falling back to $FALLBACK_DB_DIR"
  DB_DIR="$FALLBACK_DB_DIR"
  mkdir -p "$DB_DIR"
fi

export CHROMA_PERSIST_DIR="$DB_DIR"

# Force SQLite deployments to use an async, writable DB URL.
# Keep non-SQLite URLs (for example PostgreSQL) unchanged.
case "${DATABASE_URL:-}" in
  "")
    export DATABASE_URL="sqlite+aiosqlite:///$CHROMA_PERSIST_DIR/rag_lab.db"
    ;;
  sqlite://*|sqlite+aiosqlite://*)
    export DATABASE_URL="sqlite+aiosqlite:///$CHROMA_PERSIST_DIR/rag_lab.db"
    ;;
esac

# Resolve a writable directory for file uploads.
FALLBACK_UPLOAD_DIR="/app/backend/uploads"
UPLOAD_CANDIDATE="${UPLOAD_DIR:-/data/uploads}"

mkdir -p "$UPLOAD_CANDIDATE" 2>/dev/null || true

if [ "$(id -u)" -eq 0 ]; then
  chown -R appuser:appgroup "$UPLOAD_CANDIDATE" || echo "[WARN] Could not chown $UPLOAD_CANDIDATE, continuing"
fi

if [ ! -w "$UPLOAD_CANDIDATE" ]; then
  echo "[WARN] $UPLOAD_CANDIDATE is not writable by uid $(id -u). Falling back to $FALLBACK_UPLOAD_DIR"
  UPLOAD_CANDIDATE="$FALLBACK_UPLOAD_DIR"
  mkdir -p "$UPLOAD_CANDIDATE"
fi

export UPLOAD_DIR="$UPLOAD_CANDIDATE"

# Run Alembic migrations (async-enabled env.py handles aiosqlite)
alembic upgrade head

# Exec Gunicorn
exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w ${WEB_CONCURRENCY:-4} \
  --bind 0.0.0.0:${PORT:-7860} --timeout ${GUNICORN_TIMEOUT:-120} --log-level ${LOG_LEVEL:-info} \
  --access-logfile - --error-logfile - --capture-output
