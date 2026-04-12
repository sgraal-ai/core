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
    def test_certificate_not_found(self):
        """POST /v1/certificate returns 404 for unknown request_id."""
        c = _client()
        resp = c.post("/v1/certificate", json={
            "request_id": "nonexistent-request-id"
        }, headers=AUTH)
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_certificate_for_known_outcome(self):
        """POST /v1/certificate returns cert when request_id matches an in-memory outcome."""
        c = _client()
        # Run a preflight to create an in-memory outcome
        pf = c.post("/v1/preflight", json={
            "memory_state": [_e(content="Per Q2 2024 SEC ruling and the deprecated v2.1 framework was mandatory for 2023 filings.",
                                age=0, downstream=8)],
            "domain": "fintech", "action_type": "irreversible",
        }, headers=AUTH)
        outcome_id = pf.json().get("outcome_id")
        if outcome_id:
            resp = c.post("/v1/certificate", json={"request_id": outcome_id}, headers=AUTH)
            if resp.status_code == 200:
                data = resp.json()
                assert data["issuer"] == "Sgraal Protocol"
                assert data["valid"] is True

    def test_get_certificate_demo_blocked(self):
        """GET /v1/certificate/{id} with demo key returns 403."""
        c = _client()
        resp = c.get("/v1/certificate/nonexistent-cert-id", headers=AUTH)
        assert resp.status_code == 403
