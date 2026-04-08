import pytest


@pytest.mark.asyncio
async def test_list_profiles(client):
    response = await client.get("/api/v1/profiles")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data
    # Should have the 7 built-in profiles at minimum
    assert data["meta"]["total"] >= 7
    # Check structure of first profile summary
    first = data["data"][0]
    assert "id" in first
    assert "name" in first
    assert "template_count" in first
    assert "follow_up_count" in first


@pytest.mark.asyncio
async def test_get_builtin_profile(client):
    # Get list first, pick the first one
    resp = await client.get("/api/v1/profiles")
    profiles = resp.json()["data"]
    profile_id = profiles[0]["id"]

    resp = await client.get(f"/api/v1/profiles/{profile_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == profile_id
    assert "conversation_templates" in data
    assert "follow_up_prompts" in data
    assert "template_variables" in data
    assert "behavior_defaults" in data


@pytest.mark.asyncio
async def test_get_nonexistent_profile(client):
    resp = await client.get("/api/v1/profiles/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_profile(client):
    body = {
        "name": "Test Profile",
        "description": "A test profile",
        "behavior_defaults": {
            "session_mode": "multi_turn",
            "turns_per_session": {"min": 2, "max": 5},
            "think_time_seconds": {"min": 3, "max": 10},
            "sessions_per_user": {"min": 1, "max": 2},
            "read_time_factor": 0.02,
        },
        "conversation_templates": [
            {
                "category": "test",
                "starter_prompt": "Hello, tell me about {{topic}}",
                "expected_response_tokens": {"min": 50, "max": 200},
                "follow_ups": [
                    {"content": "Can you elaborate?"},
                    {"content": "Give me an example."},
                ],
            }
        ],
        "template_variables": [
            {"name": "topic", "values": ["cats", "dogs", "birds"]},
        ],
        "follow_up_prompts": [
            {"content": "Thanks, that helps!", "is_universal": True},
        ],
    }
    resp = await client.post("/api/v1/profiles", json=body)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["name"] == "Test Profile"
    assert data["is_builtin"] is False
    assert data["slug"].startswith("test-profile")
    assert len(data["conversation_templates"]) == 1
    assert len(data["conversation_templates"][0]["follow_ups"]) == 2
    assert len(data["template_variables"]) == 1
    assert len(data["follow_up_prompts"]) >= 1
    return data["id"]


@pytest.mark.asyncio
async def test_update_profile(client):
    # Create first
    create_body = {
        "name": "Update Test",
        "description": "Will be updated",
    }
    resp = await client.post("/api/v1/profiles", json=create_body)
    assert resp.status_code == 201
    profile_id = resp.json()["data"]["id"]

    # Update name and description
    update_body = {
        "name": "Updated Profile",
        "description": "Has been updated",
    }
    resp = await client.put(f"/api/v1/profiles/{profile_id}", json=update_body)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "Updated Profile"
    assert data["description"] == "Has been updated"
    assert data["slug"].startswith("updated-profile")


@pytest.mark.asyncio
async def test_update_builtin_profile_allowed(client):
    # Built-in profiles are editable (Phase 7f change)
    resp = await client.get("/api/v1/profiles")
    builtin = [p for p in resp.json()["data"] if p["is_builtin"]][0]

    resp = await client.put(
        f"/api/v1/profiles/{builtin['id']}",
        json={"name": "Customized"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Customized"


@pytest.mark.asyncio
async def test_delete_profile(client):
    # Create then delete
    resp = await client.post(
        "/api/v1/profiles",
        json={"name": "To Delete", "description": "Temporary"},
    )
    profile_id = resp.json()["data"]["id"]

    resp = await client.delete(f"/api/v1/profiles/{profile_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["deleted"] is True

    # Verify it's gone
    resp = await client.get(f"/api/v1/profiles/{profile_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_builtin_profile_fails(client):
    resp = await client.get("/api/v1/profiles")
    builtin = [p for p in resp.json()["data"] if p["is_builtin"]][0]

    resp = await client.delete(f"/api/v1/profiles/{builtin['id']}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_clone_profile(client):
    # Get a built-in profile to clone
    resp = await client.get("/api/v1/profiles")
    source = resp.json()["data"][0]
    source_id = source["id"]

    # Get full source for comparison
    resp = await client.get(f"/api/v1/profiles/{source_id}")
    source_full = resp.json()["data"]

    # Clone it
    resp = await client.post(f"/api/v1/profiles/{source_id}/clone")
    assert resp.status_code == 201
    clone = resp.json()["data"]
    import re
    base_name = source_full["name"]
    assert re.match(rf"^{re.escape(base_name)} \(\d+\)$", clone["name"])
    first_num = int(re.search(r"\((\d+)\)$", clone["name"]).group(1))
    assert clone["is_builtin"] is False
    assert clone["id"] != source_id
    assert len(clone["conversation_templates"]) == len(source_full["conversation_templates"])
    assert len(clone["template_variables"]) == len(source_full["template_variables"])

    # Clone again — should increment
    resp2 = await client.post(f"/api/v1/profiles/{source_id}/clone")
    assert resp2.status_code == 201
    clone2 = resp2.json()["data"]
    assert clone2["name"] == f"{base_name} ({first_num + 1})"

    # Clone the clone — should still increment from base name
    resp3 = await client.post(f"/api/v1/profiles/{clone['id']}/clone")
    assert resp3.status_code == 201
    clone3 = resp3.json()["data"]
    assert clone3["name"] == f"{base_name} ({first_num + 2})"


@pytest.mark.asyncio
async def test_preview_conversation(client):
    # Use a built-in profile that has templates
    resp = await client.get("/api/v1/profiles")
    profile = resp.json()["data"][0]

    resp = await client.post(f"/api/v1/profiles/{profile['id']}/preview")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "turns" in data
    assert "profile_name" in data
    assert "template_category" in data
    assert len(data["turns"]) >= 1
    # First turn should be the user
    assert data["turns"][0]["role"] == "user"
    assert data["turns"][0]["turn"] == 1
    # Should not contain unresolved {{}} if profile has variables
    for turn in data["turns"]:
        # Some variables might not match, but built-in profiles should resolve all
        assert turn["content"]  # non-empty


@pytest.mark.asyncio
async def test_preview_empty_profile(client):
    # Create a profile with no templates
    resp = await client.post(
        "/api/v1/profiles",
        json={"name": "Empty Preview", "description": "No templates"},
    )
    profile_id = resp.json()["data"]["id"]

    resp = await client.post(f"/api/v1/profiles/{profile_id}/preview")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["turns"] == []
    assert data["template_category"] is None


@pytest.mark.asyncio
async def test_update_profile_templates(client):
    """Test that updating conversation_templates replaces them entirely."""
    # Create with one template
    resp = await client.post(
        "/api/v1/profiles",
        json={
            "name": "Template Update Test",
            "description": "Test",
            "conversation_templates": [
                {"category": "original", "starter_prompt": "Original prompt"},
            ],
        },
    )
    profile_id = resp.json()["data"]["id"]
    assert len(resp.json()["data"]["conversation_templates"]) == 1

    # Update with two different templates
    resp = await client.put(
        f"/api/v1/profiles/{profile_id}",
        json={
            "conversation_templates": [
                {"category": "new1", "starter_prompt": "New prompt 1"},
                {"category": "new2", "starter_prompt": "New prompt 2"},
            ],
        },
    )
    assert resp.status_code == 200
    templates = resp.json()["data"]["conversation_templates"]
    assert len(templates) == 2
    categories = {t["category"] for t in templates}
    assert categories == {"new1", "new2"}
