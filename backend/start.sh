#!/bin/sh
set -e

# ---------------------------------------------------------------------------
# Resolve a writable persist directory for SQLite + Chroma files.
#
# Priority:
#   1. CHROMA_PERSIST_DIR env-var (explicit override)
#   2. /data              (HF Spaces persistent storage root)
#   3. /data/chroma_data  (legacy subdir â€” may not be mkdir-able)
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

# Determine persistent storage root (prioritize /data on HF Spaces)
PERSIST_BASE=""
if _try_dir "/data"; then
  PERSIST_BASE="/data"
  echo "[INFO] Using /data as persistent storage base"
elif [ -n "${CHROMA_PERSIST_DIR:-}" ] && _try_dir "$CHROMA_PERSIST_DIR"; then
  PERSIST_BASE="$CHROMA_PERSIST_DIR"
  echo "[INFO] Using $CHROMA_PERSIST_DIR as persistent storage base"
else
  echo "[WARN] /data is not writable by uid $(id -u). Falling back to $FALLBACK_DB_DIR"
  PERSIST_BASE="$FALLBACK_DB_DIR"
  mkdir -p "$PERSIST_BASE"
fi

# 1. Dedicated Chroma persist directory (isolated subfolder so clearing Chroma never destroys the DB)
export CHROMA_PERSIST_DIR="${PERSIST_BASE}/chroma_data"
mkdir -p "$CHROMA_PERSIST_DIR"

# 2. Dedicated SQLite application database in PERSIST_BASE
# If an older rag_lab.db was placed inside chroma_data, safely migrate it to PERSIST_BASE
if [ -f "$PERSIST_BASE/chroma_data/rag_lab.db" ] && [ ! -f "$PERSIST_BASE/rag_lab.db" ]; then
  echo "[INFO] Migrating rag_lab.db from $PERSIST_BASE/chroma_data/ to $PERSIST_BASE/rag_lab.db"
  mv "$PERSIST_BASE/chroma_data/rag_lab.db"* "$PERSIST_BASE/" 2>/dev/null || true
fi

# Force SQLite deployments to use an async, writable DB URL in PERSIST_BASE
case "${DATABASE_URL:-}" in
  "")
    export DATABASE_URL="sqlite+aiosqlite:///$PERSIST_BASE/rag_lab.db"
    ;;
  sqlite://*|sqlite+aiosqlite://*)
    export DATABASE_URL="sqlite+aiosqlite:///$PERSIST_BASE/rag_lab.db"
    ;;
esac

# 3. Dedicated uploads directory
FALLBACK_UPLOAD_DIR="/app/backend/uploads"

if [ -n "${UPLOAD_DIR:-}" ]; then
  UPLOAD_CANDIDATE="$UPLOAD_DIR"
else
  UPLOAD_CANDIDATE="$PERSIST_BASE/uploads"
fi

if ! _try_dir "$UPLOAD_CANDIDATE"; then
  echo "[WARN] $UPLOAD_CANDIDATE is not writable by uid $(id -u). Falling back to $FALLBACK_UPLOAD_DIR"
  UPLOAD_CANDIDATE="$FALLBACK_UPLOAD_DIR"
  mkdir -p "$UPLOAD_CANDIDATE"
fi

export UPLOAD_DIR="$UPLOAD_CANDIDATE"

# Auto-heal any corrupted Chroma SQLite files from previous aborted runs
python -c "
import sqlite3, os, glob
persist = os.environ.get('CHROMA_PERSIST_DIR', '')
dirs = [persist, '/data', '/app/backend', '/app/backend/chroma_db', '/data/chroma_store', '/data/chroma_db']
checked = set()
for d in dirs:
    if not d or not os.path.exists(d): continue
    for f in glob.glob(os.path.join(d, '**', 'chroma.sqlite3'), recursive=True) + glob.glob(os.path.join(d, 'chroma.sqlite3')):
        if f in checked: continue
        checked.add(f)
        try:
            con = sqlite3.connect(f)
            cur = con.cursor()
            res = cur.execute('PRAGMA integrity_check;').fetchone()
            con.close()
            if not res or res[0] != 'ok':
                print(f'[WARN] Corrupt Chroma database detected at {f}: {res}. Auto-removing to restore service.')
                for ext in ['', '-wal', '-shm']:
                    target = f + ext
                    if os.path.exists(target):
                        try: os.remove(target)
                        except Exception: pass
        except Exception as e:
            print(f'[WARN] Corrupt Chroma database at {f}: {e}. Removing.')
            for ext in ['', '-wal', '-shm']:
                target = f + ext
                if os.path.exists(target):
                    try: os.remove(target)
                    except Exception: pass
" 2>/dev/null || true

# Run Alembic migrations (async-enabled env.py handles aiosqlite)
alembic upgrade head

# SQLite cannot safely serve multiple Gunicorn workers â€” concurrent WAL readers
# across separate process connections cause stale-read 404s and write conflicts.
# Cap at 1 worker for SQLite; honour WEB_CONCURRENCY only for PostgreSQL.
case "${DATABASE_URL:-}" in
  sqlite://*|sqlite+aiosqlite://*)
    EFFECTIVE_WORKERS=1
    echo "[INFO] SQLite detected â€” capping Gunicorn workers to 1 to prevent WAL race conditions"
    ;;
  *)
    EFFECTIVE_WORKERS="${WEB_CONCURRENCY:-4}"
    ;;
esac

# Exec Gunicorn
exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w "$EFFECTIVE_WORKERS" \
  --bind 0.0.0.0:${PORT:-7860} --timeout ${GUNICORN_TIMEOUT:-120} --log-level ${LOG_LEVEL:-info} \
  --access-logfile - --error-logfile - --capture-output
