#!/bin/sh
set -e

# Ensure the DB directory exists and is writable by the app user
DB_DIR="${CHROMA_PERSIST_DIR:-/app/backend}"
mkdir -p "$DB_DIR"

# On HF Spaces mounted volumes (for example /data), chown can be forbidden.
# Only try it as root, and never fail startup if ownership cannot be changed.
if [ "$(id -u)" -eq 0 ]; then
  chown -R appuser:appgroup "$DB_DIR" || echo "[WARN] Could not chown $DB_DIR, continuing"
fi

if [ ! -w "$DB_DIR" ]; then
  echo "[WARN] $DB_DIR is not writable by uid $(id -u). Startup may fail if SQLite writes are needed."
fi

# Run Alembic migrations (async-enabled env.py handles aiosqlite)
alembic upgrade head

# Exec Gunicorn
exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w ${WEB_CONCURRENCY:-4} \
  --bind 0.0.0.0:${PORT:-7860} --timeout ${GUNICORN_TIMEOUT:-120} --log-level ${LOG_LEVEL:-info} \
  --access-logfile - --error-logfile - --capture-output
