#!/bin/sh
set -e

# ---------------------------------------------------------------------------
# Resolve a writable persist directory for SQLite + Chroma files.
#
# Priority:
#   1. CHROMA_PERSIST_DIR env-var (explicit override)
#   2. /data              (HF Spaces persistent storage root)
#   3. /data/chroma_data  (legacy subdir — may not be mkdir-able)
#   4. /app/backend/chroma_data (ephemeral fallback, wiped on restart)
# ---------------------------------------------------------------------------
FALLBACK_DB_DIR="/app/backend/chroma_data"

_try_dir() {
  # Returns 0 (success) if the directory exists and is writable, or can be
  # created and written to. Returns 1 otherwise.
  _d="$1"
  mkdir -p "$_d" 2>/dev/null || true
  [ -d "$_d" ] && [ -w "$_d" ]
}

if [ -n "${CHROMA_PERSIST_DIR:-}" ]; then
  DB_DIR="$CHROMA_PERSIST_DIR"
  _try_dir "$DB_DIR" || {
    echo "[WARN] CHROMA_PERSIST_DIR=$DB_DIR is not writable. Trying /data..."
    DB_DIR=""
  }
fi

if [ -z "${DB_DIR:-}" ]; then
  # Try /data first (HF Spaces persistent root — no subdir creation needed)
  if _try_dir "/data"; then
    DB_DIR="/data"
    echo "[INFO] Using /data as persist directory"
  elif _try_dir "/data/chroma_data"; then
    DB_DIR="/data/chroma_data"
    echo "[INFO] Using /data/chroma_data as persist directory"
  else
    echo "[WARN] /data is not writable by uid $(id -u). Falling back to $FALLBACK_DB_DIR"
    DB_DIR="$FALLBACK_DB_DIR"
    mkdir -p "$DB_DIR"
  fi
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
# Co-locate with the DB dir so uploads survive in the same persistent area.
FALLBACK_UPLOAD_DIR="/app/backend/uploads"

if [ -n "${UPLOAD_DIR:-}" ]; then
  UPLOAD_CANDIDATE="$UPLOAD_DIR"
else
  UPLOAD_CANDIDATE="$DB_DIR/uploads"
fi

if ! _try_dir "$UPLOAD_CANDIDATE"; then
  echo "[WARN] $UPLOAD_CANDIDATE is not writable by uid $(id -u). Falling back to $FALLBACK_UPLOAD_DIR"
  UPLOAD_CANDIDATE="$FALLBACK_UPLOAD_DIR"
  mkdir -p "$UPLOAD_CANDIDATE"
fi

export UPLOAD_DIR="$UPLOAD_CANDIDATE"

# Run Alembic migrations (async-enabled env.py handles aiosqlite)
alembic upgrade head

# SQLite cannot safely serve multiple Gunicorn workers — concurrent WAL readers
# across separate process connections cause stale-read 404s and write conflicts.
# Cap at 1 worker for SQLite; honour WEB_CONCURRENCY only for PostgreSQL.
case "${DATABASE_URL:-}" in
  sqlite://*|sqlite+aiosqlite://*)
    EFFECTIVE_WORKERS=1
    echo "[INFO] SQLite detected — capping Gunicorn workers to 1 to prevent WAL race conditions"
    ;;
  *)
    EFFECTIVE_WORKERS="${WEB_CONCURRENCY:-4}"
    ;;
esac

# Exec Gunicorn
exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w "$EFFECTIVE_WORKERS" \
  --bind 0.0.0.0:${PORT:-7860} --timeout ${GUNICORN_TIMEOUT:-120} --log-level ${LOG_LEVEL:-info} \
  --access-logfile - --error-logfile - --capture-output
