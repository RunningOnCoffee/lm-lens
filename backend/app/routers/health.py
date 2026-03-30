import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    # Check database
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    # Check mock LLM (best-effort, it's optional)
    mock_status = "unavailable"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get("http://lm-lens-mock:8000/health")
            if resp.status_code == 200:
                mock_status = "healthy"
    except Exception:
        mock_status = "unavailable"

    return {
        "data": {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "service": "lm-lens-api",
            "components": {
                "database": db_status,
                "mock_llm": mock_status,
            },
        }
    }
