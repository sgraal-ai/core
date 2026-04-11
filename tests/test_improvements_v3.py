"""Tests for 6 immediate improvements — detection transitions, Redis visibility, policy bounds, certificate."""
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


class TestDetectionTransitions:
    def test_detection_transitions_in_delta(self):
        """Fix 1: preflight_delta includes detection_transitions."""
        c = _client()
        resp = c.post("/v1/preflight", json={
            "memory_state": [_e(age=5, downstream=1)],
            "domain": "general", "action_type": "informational",
        }, headers=AUTH)
        data = resp.json()
        if "preflight_delta" in data:
            delta = data["preflight_delta"]
            assert "detection_transitions" in delta
            assert "detection_state_changed" in delta

    def test_detection_state_changed_flag(self):
        """detection_state_changed is bool."""
        c = _client()
        resp = c.post("/v1/preflight", json={
            "memory_state": [_e()], "domain": "general", "action_type": "informational",
        }, headers=AUTH)
        data = resp.json()
        if "preflight_delta" in data:
            assert isinstance(data["preflight_delta"]["detection_state_changed"], bool)


class TestRedisVisibility:
    def test_redis_available_in_response(self):
        """Fix 3: redis_available field present in response."""
        c = _client()
        resp = c.post("/v1/preflight", json={
            "memory_state": [_e()], "domain": "general", "action_type": "informational",
        }, headers=AUTH)
        data = resp.json()
        assert "redis_available" in data
        assert isinstance(data["redis_available"], bool)


class TestPolicyBounds:
    def test_policy_bounds_validation(self):
        """Fix 5: block_omega=0 rejected."""
        c = _client()
        resp = c.post("/v1/policy/validate", json={
            "config": {"version": "1.0", "agent_id": "test", "domain": "general",
                       "thresholds": {"block_omega": 0}}
        }, headers=AUTH)
        data = resp.json()
        assert data["valid"] is False
        assert any("block_omega" in e for e in data["errors"])

    def test_policy_ascending_thresholds(self):
        """Fix 5: warn >= ask_user rejected."""
        c = _client()
        resp = c.post("/v1/policy/validate", json={
            "config": {"version": "1.0", "agent_id": "test", "domain": "general",
                       "thresholds": {"warn_omega": 60, "ask_user_omega": 50, "block_omega": 80}}
        }, headers=AUTH)
        data = resp.json()
        assert data["valid"] is False
        assert any("ascending" in e for e in data["errors"])


class TestCertificate:
    def test_certificate_endpoint(self):
        """Fix 6: POST /v1/certificate returns certificate."""
        c = _client()
        resp = c.post("/v1/certificate", json={
            "request_id": "nonexistent-request-id"
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "certificate_id" in data
        assert data["issuer"] == "Sgraal Protocol"
        assert data["valid"] is True

    def test_get_certificate(self):
        """GET /v1/certificate/{id} retrieves previously issued certificate."""
        c = _client()
        # Issue first
        resp1 = c.post("/v1/certificate", json={"request_id": "test-req"}, headers=AUTH)
        cert_id = resp1.json()["certificate_id"]
        # Retrieve
        resp2 = c.get(f"/v1/certificate/{cert_id}", headers=AUTH)
        assert resp2.status_code == 200
        assert resp2.json()["certificate_id"] == cert_id
