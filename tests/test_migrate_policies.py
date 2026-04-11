"""Tests for migrate endpoint and policy registry."""
import pytest


def _client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


AUTH = {"Authorization": "Bearer sg_demo_playground"}


class TestMigrateEndpoint:
    def test_migrate_raw_strings(self):
        c = _client()
        resp = c.post("/v1/migrate", json={
            "source_format": "raw",
            "data": ["fact one", "fact two"],
            "domain": "general",
            "action_type": "informational",
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data["entry_count"] == 2
        assert data["source_format_detected"] == "raw"
        assert "preflight_result" in data
        assert "ready_to_use" in data

    def test_migrate_mem0_format(self):
        c = _client()
        resp = c.post("/v1/migrate", json={
            "source_format": "auto",
            "data": [{"memory": "user likes coffee", "score": 0.9}],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data["source_format_detected"] == "mem0"
        assert data["ready_to_use"] is True

    def test_migrate_returns_preflight(self):
        c = _client()
        resp = c.post("/v1/migrate", json={
            "data": ["some data"],
        }, headers=AUTH)
        assert resp.status_code == 200
        pf = resp.json()["preflight_result"]
        assert "recommended_action" in pf


class TestPolicyRegistry:
    def test_policies_crud(self):
        c = _client()
        # Create
        resp = c.post("/v1/policies", json={
            "name": "test-policy",
            "config": {"version": "1.0", "agent_id": "test", "domain": "general"},
        }, headers=AUTH)
        assert resp.status_code == 200
        assert resp.json()["name"] == "test-policy"

        # Get
        resp = c.get("/v1/policies/test-policy", headers=AUTH)
        assert resp.status_code == 200
        assert resp.json()["name"] == "test-policy"

        # List
        resp = c.get("/v1/policies", headers=AUTH)
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

        # Delete
        resp = c.delete("/v1/policies/test-policy", headers=AUTH)
        assert resp.status_code == 200
        assert resp.json()["deleted"] == "test-policy"

    def test_policy_apply(self):
        c = _client()
        # Create policy first
        c.post("/v1/policies", json={
            "name": "apply-test",
            "config": {"version": "1.0", "agent_id": "test", "domain": "fintech"},
        }, headers=AUTH)

        # Apply
        resp = c.post("/v1/policies/apply-test/apply", json={
            "memory_state": [{"id": "m1", "content": "test", "type": "semantic",
                              "timestamp_age_days": 5, "source_trust": 0.9}],
            "action_type": "reversible",
        }, headers=AUTH)
        assert resp.status_code == 200
        assert "recommended_action" in resp.json()
