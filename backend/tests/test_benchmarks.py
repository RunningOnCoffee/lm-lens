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


async def _create_endpoint(client, name="Test Endpoint"):
    """Create an endpoint and return its ID."""
    body = {
        "name": name,
        "endpoint_url": "http://lm-lens-mock:8000",
        "model_name": "mock-llm",
    }
    resp = await client.post("/api/v1/endpoints", json=body)
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


async def _create_scenario(client, profile_ids, **overrides):
    """Create a scenario and return its ID."""
    body = {
        "name": overrides.get("name", "Test Scenario"),
        "profiles": [{"profile_id": pid, "user_count": 1} for pid in profile_ids],
        "load_config": overrides.get("load_config", {
            "test_mode": "stress",
            "duration_seconds": 5,
        }),
    }
    resp = await client.post("/api/v1/scenarios", json=body)
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


async def _create_benchmark(client, name_suffix=""):
    """Create a full benchmark (profile + endpoint + scenario + benchmark) and return IDs."""
    profile_id = await _create_profile(client, f"BenchProfile{name_suffix}")
    endpoint_id = await _create_endpoint(client, f"BenchEndpoint{name_suffix}")
    scenario_id = await _create_scenario(client, [profile_id], name=f"BenchScenario{name_suffix}")

    resp = await client.post("/api/v1/benchmarks", json={
        "scenario_id": scenario_id,
        "endpoint_id": endpoint_id,
    })
    assert resp.status_code == 201
    bench_id = resp.json()["data"]["id"]
    return bench_id, scenario_id, endpoint_id, profile_id


# ---------------------------------------------------------------------------
# Core Benchmark Tests
# ---------------------------------------------------------------------------

async def test_start_benchmark(client):
    """POST /api/v1/benchmarks creates a benchmark."""
    profile_id = await _create_profile(client)
    endpoint_id = await _create_endpoint(client)
    scenario_id = await _create_scenario(client, [profile_id])

    resp = await client.post("/api/v1/benchmarks", json={
        "scenario_id": scenario_id,
        "endpoint_id": endpoint_id,
    })
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["scenario_id"] == scenario_id
    assert data["endpoint_id"] == endpoint_id
    assert data["status"] in ("pending", "running")
    assert data["scenario_snapshot"] is not None
    assert data["scenario_name"] == "Test Scenario"


async def test_start_benchmark_invalid_scenario(client):
    """POST /api/v1/benchmarks with nonexistent scenario returns 404."""
    endpoint_id = await _create_endpoint(client, "Invalid Scenario Test")
    resp = await client.post(
        "/api/v1/benchmarks",
        json={
            "scenario_id": "00000000-0000-0000-0000-000000000000",
            "endpoint_id": endpoint_id,
        },
    )
    assert resp.status_code == 404


async def test_list_benchmarks(client):
    """GET /api/v1/benchmarks lists created benchmarks."""
    bench_id, _, _, _ = await _create_benchmark(client, "List")

    resp = await client.get("/api/v1/benchmarks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["meta"]["total"] >= 1
    assert any(b["id"] == bench_id for b in data["data"])


async def test_get_benchmark(client):
    """GET /api/v1/benchmarks/{id} returns benchmark details."""
    bench_id, _, _, _ = await _create_benchmark(client, "Get")

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
    bench_id, _, _, _ = await _create_benchmark(client, "Delete")

    resp = await client.delete(f"/api/v1/benchmarks/{bench_id}")
    assert resp.status_code == 200

    # Verify it's gone
    resp = await client.get(f"/api/v1/benchmarks/{bench_id}")
    assert resp.status_code == 404


async def test_abort_benchmark(client):
    """POST /api/v1/benchmarks/{id}/abort on a pending/running benchmark."""
    bench_id, _, _, _ = await _create_benchmark(client, "Abort")

    resp = await client.post(f"/api/v1/benchmarks/{bench_id}/abort")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] in ("aborting", "aborted")


# ---------------------------------------------------------------------------
# Paginated Requests Tests
# ---------------------------------------------------------------------------

async def test_get_requests_empty(client):
    """GET /requests returns empty list for benchmark with no requests."""
    bench_id, _, _, _ = await _create_benchmark(client, "ReqEmpty")

    resp = await client.get(f"/api/v1/benchmarks/{bench_id}/requests")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"] == []
    assert data["meta"]["total"] == 0
    assert data["meta"]["page"] == 1


async def test_get_requests_pagination_params(client):
    """GET /requests respects page and per_page query params."""
    bench_id, _, _, _ = await _create_benchmark(client, "ReqPage")

    resp = await client.get(f"/api/v1/benchmarks/{bench_id}/requests?page=1&per_page=10")
    assert resp.status_code == 200
    meta = resp.json()["meta"]
    assert meta["page"] == 1
    assert meta["per_page"] == 10


async def test_get_requests_sort(client):
    """GET /requests accepts sort_by and sort_dir params."""
    bench_id, _, _, _ = await _create_benchmark(client, "ReqSort")

    resp = await client.get(f"/api/v1/benchmarks/{bench_id}/requests?sort_by=ttft_ms&sort_dir=desc")
    assert resp.status_code == 200


async def test_get_requests_filter_success(client):
    """GET /requests accepts success filter."""
    bench_id, _, _, _ = await _create_benchmark(client, "ReqFilter")

    resp = await client.get(f"/api/v1/benchmarks/{bench_id}/requests?success=true")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Histogram Tests
# ---------------------------------------------------------------------------

async def test_histogram_empty(client):
    """GET /histogram returns empty bins for benchmark with no requests."""
    bench_id, _, _, _ = await _create_benchmark(client, "HistEmpty")

    resp = await client.get(f"/api/v1/benchmarks/{bench_id}/histogram")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["bins"] == []


async def test_histogram_invalid_metric(client):
    """GET /histogram with invalid metric returns 400."""
    bench_id, _, _, _ = await _create_benchmark(client, "HistBad")

    resp = await client.get(f"/api/v1/benchmarks/{bench_id}/histogram?metric=invalid")
    assert resp.status_code == 400


async def test_histogram_valid_metrics(client):
    """GET /histogram accepts ttft_ms, tgt_ms, tokens_per_second."""
    bench_id, _, _, _ = await _create_benchmark(client, "HistMetrics")

    for metric in ["ttft_ms", "tgt_ms", "tokens_per_second"]:
        resp = await client.get(f"/api/v1/benchmarks/{bench_id}/histogram?metric={metric}")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Profile Stats Tests
# ---------------------------------------------------------------------------

async def test_profile_stats_empty(client):
    """GET /profile-stats returns empty list for benchmark with no requests."""
    bench_id, _, _, _ = await _create_benchmark(client, "ProfEmpty")

    resp = await client.get(f"/api/v1/benchmarks/{bench_id}/profile-stats")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


# ---------------------------------------------------------------------------
# Compare Tests
# ---------------------------------------------------------------------------

async def test_compare_two_benchmarks(client):
    """GET /compare returns data for two valid benchmarks."""
    bench_a, _, _, _ = await _create_benchmark(client, "CmpA")
    bench_b, _, _, _ = await _create_benchmark(client, "CmpB")

    resp = await client.get(f"/api/v1/benchmarks/compare?ids={bench_a},{bench_b}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["benchmarks"]) == 2


async def test_compare_wrong_count(client):
    """GET /compare with 1 or 3 IDs returns 400."""
    bench_id, _, _, _ = await _create_benchmark(client, "CmpBad")

    resp = await client.get(f"/api/v1/benchmarks/compare?ids={bench_id}")
    assert resp.status_code == 400


async def test_compare_invalid_uuid(client):
    """GET /compare with invalid UUIDs returns 400."""
    resp = await client.get("/api/v1/benchmarks/compare?ids=not-a-uuid,also-bad")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Export Tests
# ---------------------------------------------------------------------------

async def test_export_json(client):
    """GET /export/{id}?format=json returns JSON data."""
    bench_id, _, _, _ = await _create_benchmark(client, "ExpJSON")

    resp = await client.get(f"/api/v1/benchmarks/export/{bench_id}?format=json")
    assert resp.status_code == 200
    assert "data" in resp.json()


async def test_export_csv(client):
    """GET /export/{id}?format=csv returns CSV content."""
    bench_id, _, _, _ = await _create_benchmark(client, "ExpCSV")

    resp = await client.get(f"/api/v1/benchmarks/export/{bench_id}?format=csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    content = resp.text
    assert "profile_name" in content  # CSV header


async def test_export_not_found(client):
    """GET /export/{id} with nonexistent ID returns 404."""
    resp = await client.get("/api/v1/benchmarks/export/00000000-0000-0000-0000-000000000000?format=json")
    assert resp.status_code == 404
