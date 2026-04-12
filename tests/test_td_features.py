"""Tests for TD schedulers, sleeper alerts, action checkpoint."""
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


class TestSchedulerHealth:
    def test_truth_scheduler_in_health(self):
        c = _client()
        resp = c.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "truth_subscription_scheduler" in data
        assert data["truth_subscription_scheduler"] == "running"


class TestSleeperAlerts:
    def test_sleeper_alerts_endpoint(self):
        c = _client()
        resp = c.get("/v1/sleeper/alerts", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "alerts" in data
        assert "count" in data


class TestActionCheckpoint:
    def test_action_checkpoint_present(self):
        """action_context in request → action_checkpoint in response."""
        c = _client()
        resp = c.post("/v1/preflight", json={
            "memory_state": [_e(age=5, downstream=1)],
            "domain": "general", "action_type": "reversible",
            "action_context": "send email to customer",
        }, headers=AUTH)
        data = resp.json()
        assert "action_checkpoint" in data
        assert data["action_checkpoint"]["tool_risk_level"] == "MEDIUM"

    def test_tool_risk_critical(self):
        """'wire transfer' → CRITICAL."""
        c = _client()
        resp = c.post("/v1/preflight", json={
            "memory_state": [_e(age=5, downstream=1)],
            "domain": "fintech", "action_type": "irreversible",
            "action_context": "execute wire transfer to external account",
        }, headers=AUTH)
        data = resp.json()
        assert data["action_checkpoint"]["tool_risk_level"] == "CRITICAL"

    def test_tool_risk_low(self):
        """Generic context → LOW."""
        c = _client()
        resp = c.post("/v1/preflight", json={
            "memory_state": [_e(age=5, downstream=1)],
            "domain": "general", "action_type": "informational",
            "action_context": "read customer profile",
        }, headers=AUTH)
        data = resp.json()
        assert data["action_checkpoint"]["tool_risk_level"] == "LOW"
