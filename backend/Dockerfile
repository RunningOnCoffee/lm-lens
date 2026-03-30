FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .

# Install dependencies only (not the project itself)
RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.30.0" \
    "sqlalchemy[asyncio]>=2.0.0" \
    "asyncpg>=0.30.0" \
    "alembic>=1.14.0" \
    "pydantic>=2.10.0" \
    "pydantic-settings>=2.6.0" \
    "httpx>=0.28.0" \
    "websockets>=14.0" \
    "pytest>=8.0.0" \
    "pytest-asyncio>=0.24.0"

COPY app/ app/
COPY alembic/ alembic/
COPY tests/ tests/
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENV PYTHONPATH=/app

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
