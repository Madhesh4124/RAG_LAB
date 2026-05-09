#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -x ".venv/Scripts/python.exe" ]]; then
  echo "Missing backend/.venv/Scripts/python.exe"
  echo "Create the backend virtual environment first, then rerun this script."
  exit 1
fi

export LOG_FORMAT="${LOG_FORMAT:-text}"
export LOG_LEVEL="${LOG_LEVEL:-info}"
export PYTHONUNBUFFERED=1

# Fast dev reloads: skip startup migration work unless you explicitly opt in.
export RUN_ALEMBIC_MIGRATIONS="${RUN_ALEMBIC_MIGRATIONS:-0}"
export RUN_BOOTSTRAP_MIGRATIONS="${RUN_BOOTSTRAP_MIGRATIONS:-0}"

exec ./.venv/Scripts/python.exe -m uvicorn app.main:app \
  --reload \
  --host 127.0.0.1 \
  --port 8000 \
  --reload-dir app \
  --log-level "${LOG_LEVEL}" \
  --access-log
