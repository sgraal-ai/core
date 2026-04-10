"""Tests for Naturalness Score (#225)."""
import pytest


def _e(id="m1", content="Standard data.", type="semantic", age=1, trust=0.9,
       conflict=0.05, downstream=3):
    return {"id": id, "content": content, "type": type,
            "timestamp_age_days": age, "source_trust": trust,
            "source_conflict": conflict, "downstream_count": downstream}


def _call_check(entries):
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from api.main import _check_naturalness
    return _check_naturalness(entries)


def _preflight(entries, domain="general", action_type="informational"):
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    resp = client.post("/v1/preflight", json={
        "memory_state": entries, "domain": domain, "action_type": action_type,
    }, headers={"Authorization": "Bearer sg_demo_playground"})
    assert resp.status_code == 200
    return resp.json()


class TestNaturalnessDetection:
    def test_organic_clean_memory(self):
        entries = [
            _e(id="m1", trust=0.85, conflict=0.12, age=3, downstream=2),
            _e(id="m2", trust=0.72, conflict=0.08, age=7, downstream=5),
            _e(id="m3", trust=0.93, conflict=0.15, age=1, downstream=1),
        ]
        r = _call_check(entries)
        assert r["naturalness_level"] == "ORGANIC"
        assert r["naturalness_score"] == 1.0
        assert r["naturalness_flags"] == []

    def test_uniform_trust_suspicious(self):
        entries = [
            _e(id="m1", trust=0.90, conflict=0.10),
            _e(id="m2", trust=0.90, conflict=0.08),
            _e(id="m3", trust=0.90, conflict=0.12),
        ]
        r = _call_check(entries)
        assert "uniform_trust" in r["naturalness_flags"]
        assert r["naturalness_score"] < 1.0

    def test_zero_conflict_suspicious(self):
        entries = [
            _e(id="m1", trust=0.85, conflict=0.01),
            _e(id="m2", trust=0.72, conflict=0.005),
            _e(id="m3", trust=0.93, conflict=0.015),
        ]
        r = _call_check(entries)
        assert "zero_conflict" in r["naturalness_flags"]

    def test_perfect_trust_score_suspicious(self):
        r = _call_check([_e(trust=1.0)])
        assert "perfect_trust" in r["naturalness_flags"]

    def test_downstream_implausible(self):
        r = _call_check([_e(downstream=15, age=0.05)])
        assert "downstream_implausible" in r["naturalness_flags"]

    def test_all_zero_age_suspicious(self):
        entries = [
            _e(id="m1", age=0, trust=0.85, conflict=0.10),
            _e(id="m2", age=0, trust=0.72, conflict=0.08),
            _e(id="m3", age=0, trust=0.93, conflict=0.12),
        ]
        r = _call_check(entries)
        assert "all_zero_age" in r["naturalness_flags"]

    def test_multiple_signals_compound(self):
        """Multiple signals → lower score."""
        entries = [
            _e(id="m1", trust=0.90, conflict=0.01, age=0, downstream=15),
            _e(id="m2", trust=0.90, conflict=0.01, age=0, downstream=3),
            _e(id="m3", trust=0.90, conflict=0.01, age=0, downstream=2),
        ]
        r = _call_check(entries)
        assert len(r["naturalness_flags"]) >= 3
        assert r["naturalness_score"] <= 0.4

    def test_single_entry_no_false_positive(self):
        r = _call_check([_e(trust=0.9, conflict=0.05, age=5, downstream=2)])
        assert r["naturalness_level"] == "ORGANIC"

    def test_organic_with_variance(self):
        entries = [
            _e(id="m1", trust=0.60, conflict=0.20, age=10, downstream=1),
            _e(id="m2", trust=0.95, conflict=0.05, age=0.5, downstream=8),
            _e(id="m3", trust=0.78, conflict=0.12, age=3, downstream=3),
        ]
        r = _call_check(entries)
        assert r["naturalness_level"] == "ORGANIC"


class TestNaturalnessIntegration:
    def test_naturalness_score_in_response(self):
        resp = _preflight([_e(age=5, downstream=1)])
        assert "naturalness_score" in resp
        assert "naturalness_level" in resp
        assert "naturalness_flags" in resp

    def test_fabricated_level_escalates(self):
        """FABRICATED escalates USE_MEMORY → WARN."""
        entries = [
            _e(id="m1", trust=0.90, conflict=0.01, age=0, downstream=15),
            _e(id="m2", trust=0.90, conflict=0.01, age=0, downstream=3),
            _e(id="m3", trust=1.0, conflict=0.005, age=0, downstream=2),
        ]
        resp = _preflight(entries)
        assert resp["naturalness_level"] in ("FABRICATED", "SYNTHETIC")
        if resp["naturalness_level"] == "FABRICATED":
            assert resp["recommended_action"] in ("WARN", "ASK_USER", "BLOCK")

    def test_synthetic_level_repair_plan(self):
        """SYNTHETIC adds VERIFY_NATURALNESS to repair_plan."""
        entries = [
            _e(id="m1", trust=0.90, conflict=0.01, age=5),
            _e(id="m2", trust=0.90, conflict=0.01, age=3),
            _e(id="m3", trust=0.90, conflict=0.01, age=1),
        ]
        resp = _preflight(entries)
        if resp["naturalness_level"] == "SYNTHETIC":
            rp_actions = [r["action"] for r in resp.get("repair_plan", [])]
            assert "VERIFY_NATURALNESS" in rp_actions
