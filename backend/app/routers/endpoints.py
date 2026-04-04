import re
import time
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.endpoint import Endpoint
from app.schemas.endpoint import (
    EndpointCreate,
    EndpointRead,
    EndpointSummary,
    EndpointTestRequest,
    EndpointTestResponse,
    EndpointUpdate,
)

router = APIRouter(prefix="/endpoints", tags=["endpoints"])
endpoint_test_router = APIRouter(prefix="/endpoint", tags=["endpoint"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_endpoint_or_404(endpoint_id: UUID, db: AsyncSession) -> Endpoint:
    result = await db.execute(select(Endpoint).where(Endpoint.id == endpoint_id))
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return endpoint


async def _next_clone_name(source_name: str, db: AsyncSession) -> str:
    base = re.sub(r"\s*\(\d+\)\s*$", "", source_name).strip()
    pattern = f"{base} (%"
    result = await db.execute(
        select(Endpoint.name).where(Endpoint.name.like(pattern))
    )
    existing = {row[0] for row in result.all()}
    n = 1
    while f"{base} ({n})" in existing:
        n += 1
    return f"{base} ({n})"


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@router.get("", response_model=dict)
async def list_endpoints(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        select(Endpoint).order_by(Endpoint.created_at.desc())
    )
    endpoints = result.scalars().all()

    summaries = [
        EndpointSummary.model_validate(e).model_dump(mode="json")
        for e in endpoints
    ]
    return {"data": summaries, "meta": {"total": len(summaries)}}


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------

@router.get("/{endpoint_id}", response_model=dict)
async def get_endpoint(endpoint_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    endpoint = await _get_endpoint_or_404(endpoint_id, db)
    return {"data": EndpointRead.model_validate(endpoint).model_dump(mode="json")}


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@router.post("", response_model=dict, status_code=201)
async def create_endpoint(body: EndpointCreate, db: AsyncSession = Depends(get_db)) -> dict:
    endpoint = Endpoint(
        name=body.name,
        endpoint_url=body.endpoint_url,
        api_key=body.api_key,
        model_name=body.model_name,
        gpu=body.gpu,
        inference_engine=body.inference_engine,
        notes=body.notes,
    )
    db.add(endpoint)
    await db.commit()
    await db.refresh(endpoint)
    return {"data": EndpointRead.model_validate(endpoint).model_dump(mode="json")}


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@router.put("/{endpoint_id}", response_model=dict)
async def update_endpoint(
    endpoint_id: UUID, body: EndpointUpdate, db: AsyncSession = Depends(get_db)
) -> dict:
    endpoint = await _get_endpoint_or_404(endpoint_id, db)

    for field in ("name", "endpoint_url", "api_key", "model_name", "gpu", "inference_engine", "notes"):
        value = getattr(body, field)
        if value is not None:
            setattr(endpoint, field, value)

    await db.commit()
    await db.refresh(endpoint)
    return {"data": EndpointRead.model_validate(endpoint).model_dump(mode="json")}


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete("/{endpoint_id}", response_model=dict)
async def delete_endpoint(endpoint_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    endpoint = await _get_endpoint_or_404(endpoint_id, db)
    await db.delete(endpoint)
    await db.commit()
    return {"data": {"deleted": True}}


# ---------------------------------------------------------------------------
# Clone
# ---------------------------------------------------------------------------

@router.post("/{endpoint_id}/clone", response_model=dict, status_code=201)
async def clone_endpoint(endpoint_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    source = await _get_endpoint_or_404(endpoint_id, db)
    clone_name = await _next_clone_name(source.name, db)

    clone = Endpoint(
        name=clone_name,
        endpoint_url=source.endpoint_url,
        api_key=source.api_key,
        model_name=source.model_name,
        gpu=source.gpu,
        inference_engine=source.inference_engine,
        notes=source.notes,
    )
    db.add(clone)
    await db.commit()
    await db.refresh(clone)
    return {"data": EndpointRead.model_validate(clone).model_dump(mode="json")}


# ---------------------------------------------------------------------------
# Endpoint Test (mounted at /api/v1/endpoint)
# ---------------------------------------------------------------------------

@endpoint_test_router.post("/test", response_model=dict)
async def test_endpoint(body: EndpointTestRequest) -> dict:
    """Send a minimal chat completion request to test connectivity."""
    url = body.endpoint_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        if not url.endswith("/v1"):
            url += "/v1"
        url += "/chat/completions"

    headers = {"Content-Type": "application/json"}
    if body.api_key:
        headers["Authorization"] = f"Bearer {body.api_key}"

    payload = {
        "model": body.model_name,
        "messages": [{"role": "user", "content": "Say hello."}],
        "max_tokens": 5,
    }

    try:
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            resp = await client.post(url, json=payload, headers=headers)
        latency_ms = (time.perf_counter() - start) * 1000

        if resp.status_code >= 400:
            return {
                "data": EndpointTestResponse(
                    success=False,
                    latency_ms=latency_ms,
                    error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                ).model_dump()
            }

        data = resp.json()
        model_reported = data.get("model")

        return {
            "data": EndpointTestResponse(
                success=True,
                latency_ms=round(latency_ms, 1),
                model_reported=model_reported,
            ).model_dump()
        }
    except httpx.TimeoutException:
        return {
            "data": EndpointTestResponse(
                success=False,
                error="Connection timed out after 30s",
            ).model_dump()
        }
    except httpx.ConnectError as e:
        return {
            "data": EndpointTestResponse(
                success=False,
                error=f"Connection failed: {e}",
            ).model_dump()
        }
    except Exception as e:
        return {
            "data": EndpointTestResponse(
                success=False,
                error=f"Unexpected error: {e}",
            ).model_dump()
        }
