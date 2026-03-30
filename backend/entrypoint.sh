#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
while ! python -c "
import asyncio, asyncpg
async def check():
    conn = await asyncpg.connect('postgresql://lm-lens:lm-lens@lm-lens-db:5432/lm-lens')
    await conn.close()
asyncio.run(check())
" 2>/dev/null; do
    sleep 1
done
echo "PostgreSQL is ready."

echo "Running Alembic migrations..."
cd /app && alembic -c alembic/alembic.ini upgrade head

echo "Starting LM Lens API..."
exec uvicorn app.main:app --host ${API_HOST:-0.0.0.0} --port ${API_PORT:-8000} --log-level ${LOG_LEVEL:-info}
