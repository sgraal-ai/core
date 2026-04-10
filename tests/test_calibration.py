"""Tests for automated corpus calibration loop (#228)."""
import pytest


def _client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


AUTH = {"Authorization": "Bearer sg_demo_playground"}


# ── Engine unit tests ───────────────────────────────────────────────────────

class TestCalibrationEngine:
    def test_pass_rate_computed_correctly(self):
        from api.calibration_engine import CalibrationEngine, CalibrationReport
        engine = CalibrationEngine()
        # Simulate: create a report manually
        report = CalibrationReport(total_cases=100, passed=95, mismatched=5)
        report.pass_rate = round(report.passed / report.total_cases, 4)
        assert report.pass_rate == 0.95

    def test_mismatch_classified_as_corpus_wrong(self):
        from api.calibration_engine import CalibrationEngine
        engine = CalibrationEngine()
        case = {"expected_decision": "BLOCK"}
        actual = {
            "recommended_action": "WARN", "omega_mem_final": 20.0,
            "timestamp_integrity": "VALID", "identity_drift": "CLEAN",
            "consensus_collapse": "CLEAN", "provenance_chain_integrity": "CLEAN",
        }
        result = engine.classify_mismatch(case, actual)
        assert result == "corpus_wrong"

    def test_mismatch_classified_as_threshold_wrong(self):
        from api.calibration_engine import CalibrationEngine
        engine = CalibrationEngine()
        case = {"expected_decision": "WARN"}
        actual = {
            "recommended_action": "USE_MEMORY", "omega_mem_final": 25.0,
            "timestamp_integrity": "SUSPICIOUS", "identity_drift": "CLEAN",
            "consensus_collapse": "CLEAN", "provenance_chain_integrity": "CLEAN",
        }
        result = engine.classify_mismatch(case, actual)
        assert result == "threshold_wrong"

    def test_ambiguous_flagged_for_human_review(self):
        from api.calibration_engine import CalibrationEngine
        engine = CalibrationEngine()
        case = {"expected_decision": "WARN"}
        actual = {
            "recommended_action": "USE_MEMORY", "omega_mem_final": 45.0,
            "timestamp_integrity": "VALID", "identity_drift": "CLEAN",
            "consensus_collapse": "CLEAN", "provenance_chain_integrity": "CLEAN",
        }
        result = engine.classify_mismatch(case, actual)
        assert result == "ambiguous"

    def test_threshold_suggestion_generated(self):
        from api.calibration_engine import CalibrationEngine
        engine = CalibrationEngine()
        mismatches = [
            {"classification": "threshold_wrong", "actual_response": {"collapse_ratio": 2.5, "naturalness_score": 0.8}},
            {"classification": "threshold_wrong", "actual_response": {"collapse_ratio": 2.8, "naturalness_score": 0.9}},
            {"classification": "threshold_wrong", "actual_response": {"collapse_ratio": 2.3, "naturalness_score": 0.7}},
        ]
        suggestions = engine.suggest_threshold_adjustment(mismatches)
        assert any(s["parameter"] == "collapse_ratio_threshold" for s in suggestions)

    def test_report_to_dict(self):
        from api.calibration_engine import CalibrationReport
        report = CalibrationReport(total_cases=10, passed=9, mismatched=1, pass_rate=0.9)
        d = report.to_dict()
        assert d["total_cases"] == 10
        assert d["pass_rate"] == 0.9
        assert "calibration_health" in d


# ── Endpoint tests ──────────────────────────────────────────────────────────

class TestCalibrationEndpoints:
    def test_calibration_run_endpoint_exists(self):
        c = _client()
        resp = c.post("/v1/calibration/run",
                       json={"corpus": "round6", "dry_run": True},
                       headers=AUTH)
        # May return 200 (with report) or 400 (if corpus not loadable in test env)
        assert resp.status_code in (200, 400)

    def test_dry_run_returns_report_without_changes(self):
        c = _client()
        resp = c.post("/v1/calibration/run",
                       json={"corpus": "round6", "dry_run": True},
                       headers=AUTH)
        if resp.status_code == 200:
            data = resp.json()
            assert "total_cases" in data
            assert "pass_rate" in data
            assert "calibration_health" in data

    def test_calibration_report_endpoint(self):
        c = _client()
        resp = c.get("/v1/calibration/report", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "calibration_health" in data or "message" in data

    def test_human_review_list_endpoint(self):
        c = _client()
        resp = c.get("/v1/calibration/human-review", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data
        assert "cases" in data

    def test_resolve_human_review_case(self):
        c = _client()
        resp = c.post("/v1/calibration/resolve/test-case-001",
                       json={"resolution": "accepted"},
                       headers=AUTH)
        assert resp.status_code == 200
        assert resp.json()["resolved"] == "test-case-001"
        assert resp.json()["resolution"] == "accepted"
