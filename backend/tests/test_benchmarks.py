"""Tests for the benchmark API endpoints."""

import asyncio

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_profile(client, name="Test Profile"):
    """Create a profile and return its ID."""
    body = {
        "name": name,
        "description": "Test profile for benchmarks",
        "conversation_templates": [
            {
                "category": "general",
                "starter_prompt": "Hello, tell me about testing",
            }
        ],
    }
    resp = await client.post("/api/v1/profiles", json=body)
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


async def _create_scenario(client, profile_ids, **overrides):
    """Create a scenario and return its ID."""
    body = {
        "name": overrides.get("name", "Test Scenario"),
        "endpoint_url": overrides.get("endpoint_url", "http://lm-lens-mock:8000"),
        "model_name": overrides.get("model_name", "mock-llm"),
        "profiles": [{"profile_id": pid, "user_count": 1} for pid in profile_ids],
        "load_config": overrides.get("load_config", {
            "test_mode": "stress",
            "duration_seconds": 5,
        }),
    }
    resp = await client.post("/api/v1/scenarios", json=body)
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_start_benchmark(client):
    """POST /api/v1/benchmarks creates a benchmark."""
    profile_id = await _create_profile(client)
    scenario_id = await _create_scenario(client, [profile_id])

    resp = await client.post("/api/v1/benchmarks", json={"scenario_id": scenario_id})
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["scenario_id"] == scenario_id
    assert data["status"] in ("pending", "running")
    assert data["scenario_snapshot"] is not None
    assert data["scenario_name"] == "Test Scenario"


async def test_start_benchmark_invalid_scenario(client):
    """POST /api/v1/benchmarks with nonexistent scenario returns 404."""
    resp = await client.post(
        "/api/v1/benchmarks",
        json={"scenario_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert resp.status_code == 404


async def test_list_benchmarks(client):
    """GET /api/v1/benchmarks lists created benchmarks."""
    profile_id = await _create_profile(client, "List Test Profile")
    scenario_id = await _create_scenario(client, [profile_id], name="List Test Scenario")

    await client.post("/api/v1/benchmarks", json={"scenario_id": scenario_id})

    resp = await client.get("/api/v1/benchmarks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["meta"]["total"] >= 1
    assert any(b["scenario_name"] == "List Test Scenario" for b in data["data"])


async def test_get_benchmark(client):
    """GET /api/v1/benchmarks/{id} returns benchmark details."""
    profile_id = await _create_profile(client, "Get Test Profile")
    scenario_id = await _create_scenario(client, [profile_id])

    create_resp = await client.post("/api/v1/benchmarks", json={"scenario_id": scenario_id})
    bench_id = create_resp.json()["data"]["id"]

    resp = await client.get(f"/api/v1/benchmarks/{bench_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == bench_id


async def test_get_benchmark_not_found(client):
    """GET /api/v1/benchmarks/{id} with nonexistent ID returns 404."""
    resp = await client.get("/api/v1/benchmarks/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_delete_benchmark(client):
    """DELETE /api/v1/benchmarks/{id} removes the benchmark."""
    profile_id = await _create_profile(client, "Delete Test Profile")
    scenario_id = await _create_scenario(client, [profile_id])

    create_resp = await client.post("/api/v1/benchmarks", json={"scenario_id": scenario_id})
    bench_id = create_resp.json()["data"]["id"]

    resp = await client.delete(f"/api/v1/benchmarks/{bench_id}")
    assert resp.status_code == 200

    # Verify it's gone
    resp = await client.get(f"/api/v1/benchmarks/{bench_id}")
    assert resp.status_code == 404


async def test_abort_benchmark(client):
    """POST /api/v1/benchmarks/{id}/abort on a pending/running benchmark."""
    profile_id = await _create_profile(client, "Abort Test Profile")
    scenario_id = await _create_scenario(client, [profile_id])

    create_resp = await client.post("/api/v1/benchmarks", json={"scenario_id": scenario_id})
    bench_id = create_resp.json()["data"]["id"]

    resp = await client.post(f"/api/v1/benchmarks/{bench_id}/abort")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] in ("aborting", "aborted")
