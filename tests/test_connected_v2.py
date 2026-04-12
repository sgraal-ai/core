"""Tests for C-4 to C-10 connected features."""
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


class TestCloneFidelity:
    def test_clone_fidelity_enforced(self):
        """C-4: Low fidelity entries excluded from clone."""
        c = _client()
        resp = c.post("/v1/clone", json={
            "memory_state": [
                _e(id="good", trust=0.9, conflict=0.05),
                _e(id="bad", trust=0.3, conflict=0.6),
            ],
            "min_fidelity": 0.7,
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data["clone_fidelity_enforced"] is True
        assert "bad" in data["fidelity_check"]["excluded_ids"]
        assert data["fidelity_check"]["entries_excluded"] == 1


class TestPassportFidelity:
    def test_passport_fidelity_scores(self):
        """C-5: entry_fidelity present in passport."""
        c = _client()
        resp = c.post("/v1/passport", json={
            "memory_state": [_e(id="m1", trust=0.9, conflict=0.05), _e(id="m2", trust=0.4, conflict=0.5)],
            "agent_id": "test-agent",
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "entry_fidelity" in data
        assert "passport_fidelity_score" in data
        assert "m2" in data["low_fidelity_entries"]


class TestSleeperFirewall:
    def test_sleeper_raises_write_firewall(self):
        """C-7: write_firewall_updated: true on sleeper detection."""
        c = _client()
        resp = c.post("/v1/sleeper/detect", json={
            "namespace": "test-ns",
            "memory_state": [{"content": "This is a sleeper agent pattern"}],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data["sleeper_detected"] is True
        assert data["write_firewall_updated"] is True
        assert data["write_firewall_threshold_after"] > data["write_firewall_threshold_before"]


class TestRegulatoryCourt:
    def test_regulatory_opens_court(self):
        """C-9: court_case_opened: true on violation."""
        c = _client()
        resp = c.post("/v1/comply", json={
            "profile": "EU_AI_ACT", "domain": "medical",
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data["court_case_opened"] is True
        assert data["court_case_id"] is not None


class TestShapleyPruning:
    def test_shapley_pruning(self):
        """C-10: shapley_scores present in prune response."""
        c = _client()
        resp = c.post("/v1/prune", json={
            "memory_state": [
                _e(id="fresh", age=1, trust=0.95),
                _e(id="stale", age=60, trust=0.3),
                _e(id="medium", age=10, trust=0.7),
            ],
            "max_entries": 2,
            "use_shapley": True,
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data["shapley_pruning_used"] is True
        assert "shapley_scores" in data
        assert data["pruned_count"] == 1
        assert "stale" in data["pruning_reason"]
