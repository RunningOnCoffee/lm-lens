import re

import pytest

from tests.conftest import track_created


async def _create_profile(client, name="Test Profile"):
    """Helper: create a custom profile and return its ID."""
    resp = await client.post(
        "/api/v1/profiles",
        json={"name": name, "description": f"Profile for scenario tests"},
    )
    assert resp.status_code == 201
    id_ = resp.json()["data"]["id"]
    track_created("profiles", id_)
    return id_


async def _create_scenario(client, profile_ids=None, **overrides):
    """Helper: create a scenario with sensible defaults."""
    if profile_ids is None:
        profile_ids = []
    profiles = [
        {"profile_id": pid, "user_count": 5}
        for pid in profile_ids
    ]

    body = {
        "name": overrides.get("name", "Test Scenario"),
        "profiles": profiles,
    }
    body.update({k: v for k, v in overrides.items() if k not in body})
    resp = await client.post("/api/v1/scenarios", json=body)
    if resp.status_code == 201:
        track_created("scenarios", resp.json()["data"]["id"])
    return resp


@pytest.mark.asyncio
async def test_list_scenarios_empty(client):
    response = await client.get("/api/v1/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_create_scenario(client):
    p1 = await _create_profile(client, "Scenario Profile A")
    p2 = await _create_profile(client, "Scenario Profile B")

    body = {
        "name": "Test Scenario",
        "profiles": [
            {"profile_id": p1, "user_count": 7},
            {"profile_id": p2, "user_count": 3},
        ],
    }
    resp = await client.post("/api/v1/scenarios", json=body)
    assert resp.status_code == 201
    data = resp.json()["data"]
    track_created("scenarios", data["id"])
    assert data["name"] == "Test Scenario"
    assert len(data["profiles"]) == 2
    # Check user_count and computed weight
    profiles_by_name = {p["profile_name"]: p for p in data["profiles"]}
    assert profiles_by_name["Scenario Profile A"]["user_count"] == 7
    assert profiles_by_name["Scenario Profile B"]["user_count"] == 3
    assert abs(profiles_by_name["Scenario Profile A"]["weight"] - 0.7) < 0.01
    assert abs(profiles_by_name["Scenario Profile B"]["weight"] - 0.3) < 0.01


@pytest.mark.asyncio
async def test_create_scenario_no_profiles(client):
    resp = await _create_scenario(client, profile_ids=[])
    assert resp.status_code == 201
    assert resp.json()["data"]["profiles"] == []


@pytest.mark.asyncio
async def test_create_scenario_with_load_config(client):
    body = {
        "name": "Breaking Point Test",
        "load_config": {
            "test_mode": "breaking_point",
            "duration_seconds": 300,
            "ramp_users_per_step": 2,
            "ramp_interval_seconds": 15,
            "breaking_criteria": {
                "max_ttft_ms": 3000,
                "max_itl_ms": 200,
                "max_error_rate_pct": 5.0,
            },
        },
    }
    resp = await client.post("/api/v1/scenarios", json=body)
    assert resp.status_code == 201
    data = resp.json()["data"]
    track_created("scenarios", data["id"])
    assert data["load_config"]["test_mode"] == "breaking_point"
    assert data["load_config"]["breaking_criteria"]["max_ttft_ms"] == 3000


@pytest.mark.asyncio
async def test_create_scenario_optional_max_tokens(client):
    body = {
        "name": "No Token Limit",
        "llm_params": {
            "max_tokens": None,
            "temperature": 0.5,
            "top_p": 1.0,
            "stop": [],
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        },
    }
    resp = await client.post("/api/v1/scenarios", json=body)
    assert resp.status_code == 201
    track_created("scenarios", resp.json()["data"]["id"])
    assert resp.json()["data"]["llm_params"]["max_tokens"] is None


@pytest.mark.asyncio
async def test_get_scenario(client):
    p1 = await _create_profile(client, "Get Test Profile")
    resp = await _create_scenario(client, profile_ids=[p1], name="Get Test")
    assert resp.status_code == 201
    scenario_id = resp.json()["data"]["id"]

    resp = await client.get(f"/api/v1/scenarios/{scenario_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == scenario_id
    assert data["name"] == "Get Test"
    assert len(data["profiles"]) == 1
    assert data["profiles"][0]["profile_name"] == "Get Test Profile"
    assert data["profiles"][0]["user_count"] == 5
    assert data["profiles"][0]["weight"] == 1.0


@pytest.mark.asyncio
async def test_get_nonexistent_scenario(client):
    resp = await client.get("/api/v1/scenarios/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_scenario(client):
    p1 = await _create_profile(client, "Update Scenario Profile")
    resp = await _create_scenario(client, profile_ids=[p1], name="Before Update")
    scenario_id = resp.json()["data"]["id"]

    resp = await client.put(
        f"/api/v1/scenarios/{scenario_id}",
        json={
            "name": "After Update",
            "llm_params": {"max_tokens": 2048, "temperature": 0.5, "top_p": 0.9,
                           "stop": [], "frequency_penalty": 0.0, "presence_penalty": 0.0},
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "After Update"
    assert data["llm_params"]["max_tokens"] == 2048


@pytest.mark.asyncio
async def test_delete_scenario(client):
    resp = await _create_scenario(client, name="To Delete")
    scenario_id = resp.json()["data"]["id"]

    resp = await client.delete(f"/api/v1/scenarios/{scenario_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["deleted"] is True

    resp = await client.get(f"/api/v1/scenarios/{scenario_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_clone_scenario(client):
    p1 = await _create_profile(client, "Clone Scenario Profile")
    resp = await _create_scenario(client, profile_ids=[p1], name="Original Scenario")
    source_id = resp.json()["data"]["id"]

    resp = await client.post(f"/api/v1/scenarios/{source_id}/clone")
    assert resp.status_code == 201
    clone = resp.json()["data"]
    track_created("scenarios", clone["id"])
    assert re.match(r"^Original Scenario \(\d+\)$", clone["name"])
    assert clone["id"] != source_id
    assert len(clone["profiles"]) == 1
    assert clone["profiles"][0]["user_count"] == 5

    # Clone again — should increment
    resp2 = await client.post(f"/api/v1/scenarios/{source_id}/clone")
    clone2 = resp2.json()["data"]
    track_created("scenarios", clone2["id"])
    num1 = int(re.search(r"\((\d+)\)", clone["name"]).group(1))
    num2 = int(re.search(r"\((\d+)\)", clone2["name"]).group(1))
    assert num2 == num1 + 1


@pytest.mark.asyncio
async def test_endpoint_test_bad_url(client):
    resp = await client.post(
        "/api/v1/endpoint/test",
        json={
            "endpoint_url": "http://nonexistent-host-12345:9999",
            "model_name": "test",
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["success"] is False
    assert data["error"] is not None


@pytest.mark.asyncio
async def test_list_scenario_summary_total_users(client):
    """Verify that total_users in list summary is computed from profile user_counts."""
    p1 = await _create_profile(client, "Summary Profile A")
    p2 = await _create_profile(client, "Summary Profile B")
    body = {
        "name": "Summary Test",
        "profiles": [
            {"profile_id": p1, "user_count": 7},
            {"profile_id": p2, "user_count": 3},
        ],
    }
    resp_create = await client.post("/api/v1/scenarios", json=body)
    track_created("scenarios", resp_create.json()["data"]["id"])

    resp = await client.get("/api/v1/scenarios")
    summaries = resp.json()["data"]
    summary = next(s for s in summaries if s["name"] == "Summary Test")
    assert summary["total_users"] == 10
    assert summary["profile_count"] == 2
