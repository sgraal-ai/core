"""Tests for heal_decision and stability_gauge alias fields in preflight response."""
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def _make_client():
    from api.main import app, verify_api_key
    app.dependency_overrides[verify_api_key] = lambda: {
        "customer_id": "cus_test", "tier": "test", "calls_this_month": 0, "key_hash": "testhash"
    }
    return TestClient(app), app, verify_api_key


def _preflight(client, memory_state=None):
    if memory_state is None:
        memory_state = [{"id": "e1", "content": "test", "type": "semantic",
                         "timestamp_age_days": 50, "source_trust": 0.5,
                         "source_conflict": 0.4, "downstream_count": 5}]
    resp = client.post("/v1/preflight", json={
        "memory_state": memory_state,
        "action_type": "reversible",
        "domain": "general",
    }, headers={"Authorization": "Bearer fake"})
    return resp


def test_heal_decision_matches_repair_plan():
    """heal_decision equals repair_plan[0].action when repair_plan exists."""
    client, app, verify_api_key = _make_client()
    try:
        resp = _preflight(client)
        assert resp.status_code == 200
        data = resp.json()
        assert "heal_decision" in data
        rp = data.get("repair_plan", [])
        if rp and isinstance(rp, list) and len(rp) > 0:
            assert data["heal_decision"] == rp[0]["action"]
        else:
            assert data["heal_decision"] == "NONE"
    finally:
        app.dependency_overrides.pop(verify_api_key, None)


def test_stability_gauge_matches_stability_score():
    """stability_gauge equals stability_score.score when present."""
    client, app, verify_api_key = _make_client()
    try:
        resp = _preflight(client)
        assert resp.status_code == 200
        data = resp.json()
        assert "stability_gauge" in data
        ss = data.get("stability_score")
        if ss and isinstance(ss, dict) and "score" in ss:
            assert data["stability_gauge"] == ss["score"]
        else:
            # Falls back to lyapunov or 0.0
            lv = data.get("lyapunov_stability")
            if lv and isinstance(lv, dict) and "V" in lv:
                assert data["stability_gauge"] == lv["V"]
            else:
                assert data["stability_gauge"] == 0.0
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
