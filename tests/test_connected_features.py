"""Tests for C-2 truth→forecast, C-3 forecast→heal, C-6 counterfactual→heal."""
import pytest


def _e(id="m1", content="Standard data.", type="semantic", age=1, trust=0.9,
       conflict=0.05, downstream=3):
    return {"id": id, "content": content, "type": type, "timestamp_age_days": age,
            "source_trust": trust, "source_conflict": conflict, "downstream_count": downstream}


def _client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


AUTH = {"Authorization": "Bearer sg_demo_playground"}


class TestTruthForecast:
    def test_truth_invalidate_triggers_forecast(self):
        """C-2: forecast_triggered: true in invalidate response."""
        c = _client()
        resp = c.post("/v1/truth/invalidate", json={
            "entry_ids": ["mem_001", "mem_002"],
            "domain": "fintech",
            "reason": "Source updated",
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data["forecast_triggered"] is True
        assert len(data["forecast_results"]) == 2
        assert "days_until_block" in data["forecast_results"][0]


class TestForecastAutoHeal:
    def test_forecast_auto_heal_param(self):
        """C-3: auto_heal: true triggers heal when entries are critical."""
        c = _client()
        # Entry with very low trust → will forecast as critical
        resp = c.post("/v1/forecast", json={
            "memory_state": [_e(id="m1", age=60, trust=0.1, downstream=5)],
            "domain": "fintech",
            "auto_heal": True,
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "auto_heal_triggered" in data
        assert "auto_heal_results" in data
        # With age=60 and trust=0.1, forecast should be critical
        if data["auto_heal_triggered"]:
            assert data["auto_heal_results"][0]["heal_applied"] is True

    def test_forecast_no_heal_by_default(self):
        """auto_heal defaults to false — no automatic heal."""
        c = _client()
        resp = c.post("/v1/forecast", json={
            "memory_state": [_e(id="m1", age=60, trust=0.1)],
        }, headers=AUTH)
        data = resp.json()
        assert data["auto_heal_triggered"] is False


class TestCounterfactualHeal:
    def test_counterfactual_heal_endpoint(self):
        """C-6: POST /v1/heal/counterfactual returns achieved_decision."""
        c = _client()
        resp = c.post("/v1/heal/counterfactual", json={
            "memory_state": [_e(id="m1", age=30, trust=0.5, conflict=0.3, downstream=5)],
            "domain": "general",
            "action_type": "reversible",
            "target_decision": "USE_MEMORY",
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "original_decision" in data
        assert "achieved_decision" in data
        assert "changes_applied" in data
        assert "verification_omega" in data

    def test_counterfactual_heal_applies_changes(self):
        """Stale entry (age=30) gets refreshed (age→0)."""
        c = _client()
        resp = c.post("/v1/heal/counterfactual", json={
            "memory_state": [_e(id="m1", age=30, trust=0.5)],
            "domain": "general",
            "target_decision": "USE_MEMORY",
        }, headers=AUTH)
        data = resp.json()
        if data["heal_applied"]:
            age_changes = [ch for ch in data["changes_applied"] if ch["field"] == "timestamp_age_days"]
            assert len(age_changes) > 0
            assert age_changes[0]["new_value"] == 0
