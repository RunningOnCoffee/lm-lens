"""Tests for the dashboard API endpoints."""

import pytest


@pytest.mark.anyio
async def test_dashboard_response_structure(client):
    """Dashboard returns the expected response structure."""
    resp = await client.get("/api/v1/dashboard")
    assert resp.status_code == 200
    data = resp.json()["data"]

    # Fleet overview
    fleet = data["fleet"]
    assert isinstance(fleet["total_benchmarks"], int)
    assert isinstance(fleet["total_requests"], int)
    assert isinstance(fleet["total_input_tokens"], int)
    assert isinstance(fleet["total_output_tokens"], int)
    assert fleet["avg_quality_overall"] is None or isinstance(fleet["avg_quality_overall"], float)

    # Endpoints list
    assert isinstance(data["endpoints"], list)
    for ep in data["endpoints"]:
        assert "endpoint_id" in ep
        assert "name" in ep
        assert "model_name" in ep
        assert "run_count" in ep
        assert isinstance(ep["total_input_tokens"], int)
        assert isinstance(ep["total_output_tokens"], int)

    # Profiles list
    assert isinstance(data["profiles"], list)
    for p in data["profiles"]:
        assert "profile_id" in p
        assert "profile_name" in p
        assert "avg_ttft_p50" in p
        assert "benchmark_count" in p

    # Recent runs
    assert isinstance(data["recent_runs"], list)
    assert len(data["recent_runs"]) <= 10
    for run in data["recent_runs"]:
        assert "id" in run
        assert "status" in run
        assert "scenario_name" in run


@pytest.mark.anyio
async def test_token_economy_by_endpoint(client):
    """Token economy groups by endpoint by default."""
    resp = await client.get("/api/v1/dashboard/token-economy")
    assert resp.status_code == 200
    data = resp.json()
    assert data["group_by"] == "endpoint"
    assert isinstance(data["data"], list)
    for entry in data["data"]:
        assert "group_id" in entry
        assert "group_name" in entry
        assert isinstance(entry["total_input_tokens"], int)
        assert isinstance(entry["total_output_tokens"], int)
        assert isinstance(entry["request_count"], int)


@pytest.mark.anyio
async def test_token_economy_by_profile(client):
    """Token economy accepts group_by=profile."""
    resp = await client.get("/api/v1/dashboard/token-economy?group_by=profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["group_by"] == "profile"
    assert isinstance(data["data"], list)


@pytest.mark.anyio
async def test_token_economy_invalid_group_by(client):
    """Token economy rejects invalid group_by values."""
    resp = await client.get("/api/v1/dashboard/token-economy?group_by=invalid")
    assert resp.status_code == 422
