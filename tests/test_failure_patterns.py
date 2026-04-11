"""Tests for failure patterns endpoints and memory_location field."""
import pytest


def _client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


AUTH = {"Authorization": "Bearer sg_demo_playground"}


class TestFailurePatterns:
    def test_list_failure_patterns(self):
        c = _client()
        resp = c.get("/v1/failure-patterns", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "patterns" in data
        assert data["total_corpus_cases"] == 614
        assert data["false_negative_rate"] == 0.0
        assert len(data["patterns"]) == 8

    def test_get_single_pattern(self):
        c = _client()
        resp = c.get("/v1/failure-patterns/timestamp_zeroing", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data["pattern_id"] == "timestamp_zeroing"
        assert data["round"] == 6
        assert data["detection_rate"] == 1.0

    def test_pattern_not_found(self):
        c = _client()
        resp = c.get("/v1/failure-patterns/nonexistent", headers=AUTH)
        assert resp.status_code == 404

    def test_memory_locations_present_field(self):
        c = _client()
        entry = {
            "id": "m1", "content": "Standard data.", "type": "semantic",
            "timestamp_age_days": 5, "source_trust": 0.9,
            "source_conflict": 0.05, "downstream_count": 1,
            "memory_location": "redis://agent-001/session-42"
        }
        resp = c.post("/v1/preflight", json={
            "memory_state": [entry], "domain": "general", "action_type": "informational",
        }, headers=AUTH)
        assert resp.status_code == 200
        assert resp.json()["memory_locations_present"] is True

    def test_memory_locations_absent(self):
        c = _client()
        entry = {
            "id": "m1", "content": "Standard data.", "type": "semantic",
            "timestamp_age_days": 5, "source_trust": 0.9,
            "source_conflict": 0.05, "downstream_count": 1,
        }
        resp = c.post("/v1/preflight", json={
            "memory_state": [entry], "domain": "general", "action_type": "informational",
        }, headers=AUTH)
        assert resp.status_code == 200
        assert resp.json()["memory_locations_present"] is False
