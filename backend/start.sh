#!/bin/sh
# Container entrypoint: migrate then serve API (or exec custom CMD).
set -eu
cd /app/backend

if [ "${RASHID_SKIP_MIGRATE:-0}" != "1" ]; then
  echo "alembic upgrade head..."
  alembic upgrade head
fi

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${RASHID_PORT:-8000}"
