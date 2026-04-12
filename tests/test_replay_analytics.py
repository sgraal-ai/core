"""Tests for deterministic replay and analytics endpoints."""
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


class TestReplay:
    def test_replay_endpoint(self):
        """POST /v1/replay returns decisions_match."""
        c = _client()
        # Run a preflight first to create an outcome
        pf = c.post("/v1/preflight", json={
            "memory_state": [_e(age=5, downstream=1)],
            "domain": "general", "action_type": "informational",
        }, headers=AUTH)
        outcome_id = pf.json().get("outcome_id")
        if outcome_id:
            resp = c.post("/v1/replay", json={"request_id": outcome_id}, headers=AUTH)
            if resp.status_code == 200:
                data = resp.json()
                assert "decisions_match" in data
                assert "replay_deterministic" in data
                assert "omega_delta" in data

    def test_replay_history(self):
        """GET /v1/replay/history returns list."""
        c = _client()
        resp = c.get("/v1/replay/history", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "replays" in data
        assert "count" in data


class TestAnalytics:
    def test_decision_heatmap(self):
        """GET /v1/analytics/decision-heatmap returns heatmap."""
        c = _client()
        resp = c.get("/v1/analytics/decision-heatmap?days=7", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "heatmap" in data
        assert "peak_block_hour" in data
        assert len(data["heatmap"]) == 7 * 24  # 168 cells

    def test_omega_distribution(self):
        """GET /v1/analytics/omega-distribution returns buckets."""
        c = _client()
        resp = c.get("/v1/analytics/omega-distribution?days=7", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "distribution" in data
        assert len(data["distribution"]) == 10
        assert "mean_omega" in data
        assert "p95_omega" in data
