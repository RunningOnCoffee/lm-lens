import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.database import async_session, engine
from app.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


# Registry of IDs created during the test session, keyed by table name.
# Test helpers append to this so cleanup knows exactly what to delete.
_created_ids: dict[str, list[str]] = {
    "benchmarks": [],
    "scenarios": [],
    "endpoints": [],
    "profiles": [],
}


def track_created(table: str, id_: str) -> None:
    """Register an ID for post-session cleanup."""
    _created_ids[table].append(id_)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    # Dispose engine connections after each test to avoid "operation in progress" errors
    await engine.dispose()


@pytest.fixture(autouse=True, scope="session")
async def cleanup_after_tests():
    """Delete only the rows created during this test session."""
    yield  # run all tests first

    async with async_session() as session:
        # Delete in dependency order: benchmarks → scenarios → endpoints → profiles
        for table in ["benchmarks", "scenarios", "endpoints", "profiles"]:
            ids = _created_ids[table]
            if ids:
                placeholders = ",".join(f"'{id_}'" for id_ in ids)
                await session.execute(text(
                    f"DELETE FROM {table} WHERE id IN ({placeholders})"
                ))
        await session.commit()

    await engine.dispose()
