#!/bin/sh
set -e

# Ensure the DB directory exists and is writable by the app user
mkdir -p "${CHROMA_PERSIST_DIR:-/app/backend}"
chown -R appuser:appgroup "${CHROMA_PERSIST_DIR:-/app/backend}"

# Run Alembic migrations (async-enabled env.py handles aiosqlite)
alembic upgrade head

# Exec Gunicorn
exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w ${WEB_CONCURRENCY:-4} \
  --bind 0.0.0.0:${PORT:-7860} --timeout ${GUNICORN_TIMEOUT:-120} --log-level ${LOG_LEVEL:-info} \
  --access-logfile - --error-logfile - --capture-output
