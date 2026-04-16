#!/bin/bash
set -e

# Derive a plain postgresql:// URL from DATABASE_URL for asyncpg.connect()
DB_URL="${DATABASE_URL:-postgresql+asyncpg://lm-lens:lm-lens@lm-lens-db:5432/lm-lens}"
PG_URL="${DB_URL/postgresql+asyncpg/postgresql}"

echo "Waiting for PostgreSQL..."
RETRIES=0
MAX_RETRIES=30
while ! python -c "
import asyncio, asyncpg
async def check():
    conn = await asyncpg.connect('${PG_URL}')
    await conn.close()
asyncio.run(check())
" 2>/dev/null; do
    RETRIES=$((RETRIES + 1))
    if [ "$RETRIES" -ge "$MAX_RETRIES" ]; then
        echo "ERROR: PostgreSQL not ready after ${MAX_RETRIES}s, giving up."
        exit 1
    fi
    sleep 1
done
echo "PostgreSQL is ready."

echo "Running Alembic migrations..."
cd /app && alembic -c alembic/alembic.ini upgrade head

echo "Starting LM Lens API..."
exec uvicorn app.main:app --host ${API_HOST:-0.0.0.0} --port ${API_PORT:-8000} --log-level ${LOG_LEVEL:-info}
