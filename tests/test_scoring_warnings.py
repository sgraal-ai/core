"""Tests for #1: scoring_warnings visibility.

Every bare `except Exception: pass` in preflight now captures the error
into _scoring_warnings. The response includes scoring_warnings (list)
and scoring_warnings_count (int).
"""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


class TestScoringWarnings:
    def test_scoring_warnings_present_on_every_response(self):
        """scoring_warnings and scoring_warnings_count must always appear."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{
                "id": "m1", "content": "fresh", "type": "preference",
                "timestamp_age_days": 1, "source_trust": 0.95,
                "source_conflict": 0.05, "downstream_count": 1,
            }],
            "action_type": "reversible",
            "domain": "general",
        })
        assert r.status_code == 200
        d = r.json()
        assert "scoring_warnings" in d, "scoring_warnings field missing from response"
        assert "scoring_warnings_count" in d, "scoring_warnings_count field missing"
        assert isinstance(d["scoring_warnings"], list)
        assert isinstance(d["scoring_warnings_count"], int)
        assert d["scoring_warnings_count"] == len(d["scoring_warnings"])

    def test_scoring_warnings_empty_for_healthy_input(self):
        """A simple healthy memory state should produce zero or near-zero warnings.
        Some modules legitimately fail on single-entry inputs (e.g. copula needs 2+),
        so we allow a small number, but the field must be present."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{
                "id": "m1", "content": "fresh", "type": "preference",
                "timestamp_age_days": 1, "source_trust": 0.95,
                "source_conflict": 0.05, "downstream_count": 1,
            }],
            "action_type": "reversible",
            "domain": "general",
        })
        d = r.json()
        # Allow some warnings (modules that need 2+ entries, score_history, etc.)
        # but the count must be much less than 137 (total except blocks)
        assert d["scoring_warnings_count"] < 50, (
            f"Too many scoring warnings ({d['scoring_warnings_count']}) for healthy "
            f"input — suggests a systemic issue, not individual module failures"
        )

    def test_scoring_warnings_contain_module_and_error(self):
        """Each warning entry must have 'module' and 'error' keys."""
        # Use a more complex input that might trigger some module failures
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                {"id": "m1", "content": "entry one", "type": "tool_state",
                 "timestamp_age_days": 30, "source_trust": 0.6,
                 "source_conflict": 0.4, "downstream_count": 3},
                {"id": "m2", "content": "entry two", "type": "semantic",
                 "timestamp_age_days": 10, "source_trust": 0.8,
                 "source_conflict": 0.2, "downstream_count": 2},
            ],
            "action_type": "reversible",
            "domain": "general",
            "score_history": [40, 45, 50, 55, 60, 55, 50, 45, 40, 35],
        })
        d = r.json()
        warnings = d["scoring_warnings"]
        # If any warnings exist, verify the shape
        for w in warnings:
            assert "module" in w, f"warning entry missing 'module' key: {w}"
            assert "error" in w, f"warning entry missing 'error' key: {w}"
            assert isinstance(w["module"], str)
            assert isinstance(w["error"], str)
            assert len(w["error"]) > 0, "error string should not be empty"
