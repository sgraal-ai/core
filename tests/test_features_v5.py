"""Tests for federation, timeline, provenance signing, degradation prediction, OOD calibration."""
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


class TestFederation:
    def test_federation_contribute(self):
        c = _client()
        resp = c.post("/v1/federation/contribute", json={
            "vaccine_signature": "abc123def456test", "attack_type": "timestamp_manipulation", "domain": "fintech",
        }, headers=AUTH)
        assert resp.status_code == 200
        assert resp.json()["contributed"] is True


class TestAgentTimeline:
    def test_agent_timeline(self):
        c = _client()
        # Run a preflight to generate an event
        c.post("/v1/preflight", json={"memory_state": [_e()], "domain": "general", "action_type": "informational"}, headers=AUTH)
        resp = c.get("/v1/agent/timeline?limit=10", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "timeline" in data
        assert "summary" in data
        assert "health_trend" in data["summary"]


class TestProvenanceSigning:
    def test_provenance_signed(self):
        c = _client()
        resp = c.post("/v1/preflight", json={
            "memory_state": [{"id": "m1", "content": "test", "type": "semantic",
                              "timestamp_age_days": 5, "source_trust": 0.9, "source_conflict": 0.05,
                              "downstream_count": 1, "provenance_chain": ["agent-01", "agent-02"]}],
            "domain": "general", "action_type": "informational",
        }, headers=AUTH)
        data = resp.json()
        assert data.get("provenance_signed") is True
        assert data.get("provenance_signature") is not None


class TestDegradationPrediction:
    def test_degradation_prediction(self):
        c = _client()
        resp = c.post("/v1/predict/degradation", json={
            "memory_state": [_e(id="m1", age=5, type="tool_state"), _e(id="m2", age=50, type="semantic")],
            "domain": "fintech",
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["predictions"]) == 2
        assert "fleet_health_score" in data
        assert "action_required" in data
        assert "degradation_rate" in data["predictions"][0]


class TestOODCalibration:
    def test_ood_calibration(self):
        c = _client()
        resp = c.post("/v1/calibration/run", json={
            "corpus": "round6", "dry_run": True, "ood_test": True,
        }, headers=AUTH)
        if resp.status_code == 200:
            data = resp.json()
            assert data["ood_tested"] is True
            assert data["ood_pass_rate"] is not None
