import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import async_session
from app.routers import benchmarks, health, profiles, scenarios
from app.seed_data.runner import run_seed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run seed on startup
    async with async_session() as session:
        await run_seed(session)
    yield


app = FastAPI(title="LM Lens API", version="0.1.0", lifespan=lifespan)

app.include_router(health.router, prefix="/api/v1")
app.include_router(profiles.router, prefix="/api/v1")
app.include_router(scenarios.router, prefix="/api/v1")
app.include_router(scenarios.endpoint_router, prefix="/api/v1")
app.include_router(benchmarks.router, prefix="/api/v1")
