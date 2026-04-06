"""Tests for team key creation (full key returned) and executive summary fields."""
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def _make_client():
    from api.main import app, verify_api_key
    app.dependency_overrides[verify_api_key] = lambda: {
        "customer_id": "cus_test", "tier": "test", "calls_this_month": 0, "key_hash": "testhash"
    }
    return TestClient(app), app, verify_api_key


def test_generate_key_returns_full_key():
    """POST /v1/api-keys/generate returns the full plaintext api_key."""
    client, app, verify_api_key = _make_client()
    try:
        resp = client.post("/v1/api-keys/generate",
            json={"name": "test-key"},
            headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        data = resp.json()
        assert "api_key" in data
        assert data["api_key"].startswith("sg_live_")
        assert len(data["api_key"]) > 20
        # Also returns truncated version for table display
        assert "key_truncated" in data
        assert "..." in data["key_truncated"]
        assert "name" in data
        assert data["name"] == "test-key"
    finally:
        app.dependency_overrides.pop(verify_api_key, None)


def test_preflight_has_fields_for_executive_summary():
    """Preflight response contains component_breakdown, repair_plan, recommended_action
       needed by the Executive Summary section."""
    client, app, verify_api_key = _make_client()
    try:
        resp = client.post("/v1/preflight", json={
            "memory_state": [{"id": "e1", "content": "test", "type": "semantic",
                              "timestamp_age_days": 50, "source_trust": 0.5,
                              "source_conflict": 0.4, "downstream_count": 5}],
            "action_type": "reversible",
            "domain": "general",
        }, headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        data = resp.json()
        # Executive summary needs these three fields
        assert "recommended_action" in data
        assert data["recommended_action"] in ("USE_MEMORY", "WARN", "ASK_USER", "BLOCK")
        assert "component_breakdown" in data
        assert isinstance(data["component_breakdown"], dict)
        assert len(data["component_breakdown"]) >= 5
        assert "repair_plan" in data
        assert isinstance(data["repair_plan"], list)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
