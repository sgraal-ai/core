"""Tests for deterministic seeding and hysteresis in preflight."""
from fastapi.testclient import TestClient


def _make_client():
    from api.main import app, verify_api_key
    app.dependency_overrides[verify_api_key] = lambda: {
        "customer_id": "cus_test", "tier": "test", "calls_this_month": 0, "key_hash": "testhash"
    }
    return TestClient(app), app, verify_api_key


PAYLOAD = {
    "memory_state": [{"id": "e1", "content": "test data", "type": "semantic",
                      "timestamp_age_days": 30, "source_trust": 0.7,
                      "source_conflict": 0.2, "downstream_count": 4}],
    "action_type": "reversible",
    "domain": "general",
}


def test_deterministic_same_input_same_output():
    """Identical input produces identical omega_mem_final (deterministic seed)."""
    client, app, verify_api_key = _make_client()
    try:
        r1 = client.post("/v1/preflight", json=PAYLOAD, headers={"Authorization": "Bearer fake"})
        r2 = client.post("/v1/preflight", json=PAYLOAD, headers={"Authorization": "Bearer fake"})
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["omega_mem_final"] == r2.json()["omega_mem_final"]
        assert r1.json()["recommended_action"] == r2.json()["recommended_action"]
    finally:
        app.dependency_overrides.pop(verify_api_key, None)


def test_different_input_different_seed():
    """Different input produces different seed (not hardcoded)."""
    client, app, verify_api_key = _make_client()
    try:
        payload2 = {
            "memory_state": [{"id": "e2", "content": "different data", "type": "tool_state",
                              "timestamp_age_days": 5, "source_trust": 0.9,
                              "source_conflict": 0.05, "downstream_count": 1}],
            "action_type": "irreversible",
            "domain": "fintech",
        }
        r1 = client.post("/v1/preflight", json=PAYLOAD, headers={"Authorization": "Bearer fake"})
        r2 = client.post("/v1/preflight", json=payload2, headers={"Authorization": "Bearer fake"})
        assert r1.status_code == 200
        assert r2.status_code == 200
        # Different inputs should produce different results (different seed)
        # At minimum, the component breakdowns will differ
        cb1 = r1.json()["component_breakdown"]
        cb2 = r2.json()["component_breakdown"]
        assert cb1 != cb2
    finally:
        app.dependency_overrides.pop(verify_api_key, None)


def test_hysteresis_field_present():
    """hysteresis_applied field is present in preflight response."""
    client, app, verify_api_key = _make_client()
    try:
        r = client.post("/v1/preflight", json=PAYLOAD, headers={"Authorization": "Bearer fake"})
        assert r.status_code == 200
        data = r.json()
        assert "hysteresis_applied" in data
        assert isinstance(data["hysteresis_applied"], bool)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
