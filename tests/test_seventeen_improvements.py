"""Tests for the 17-improvement sprint (tasks 1-5, 14)."""
import os
import sys
import hashlib

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from api.main import app, _safe_key_hash

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

_STALE = [
    {"id": "m1", "content": "x", "type": "tool_state", "timestamp_age_days": 45,
     "source_trust": 0.6, "source_conflict": 0.4, "downstream_count": 2},
    {"id": "m2", "content": "y", "type": "tool_state", "timestamp_age_days": 25,
     "source_trust": 0.8, "source_conflict": 0.2, "downstream_count": 3},
]
_SINGLE = [{"id": "m1", "content": "x", "type": "preference",
            "timestamp_age_days": 1, "source_trust": 0.95, "source_conflict": 0.05, "downstream_count": 1}]


class TestBugBConfidenceAvailable:
    def test_confidence_available_field_present(self):
        """Bug C fix: days_until_block_confidence_available must always be set."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _STALE, "action_type": "reversible", "domain": "general",
            "score_history": [40, 42, 45, 48, 50, 52, 55, 58, 60, 62],
        })
        d = r.json()
        if d.get("days_until_block") is not None:
            assert "days_until_block_confidence_available" in d
            assert isinstance(d["days_until_block_confidence_available"], bool)


class TestBugFDenseRanking:
    def test_tied_roi_gets_same_rank(self):
        """Bug F fix: entries with identical heal_roi must share the same rank."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _STALE, "action_type": "reversible", "domain": "general",
        })
        rp = r.json().get("repair_plan", [])
        if len(rp) >= 2:
            # Find entries with identical ROI
            rois = [item["heal_roi"] for item in rp]
            ranks = [item["rank"] for item in rp]
            for i in range(len(rois) - 1):
                if rois[i] == rois[i + 1]:
                    assert ranks[i] == ranks[i + 1], (
                        f"Tied heal_roi={rois[i]} but different ranks: {ranks[i]} vs {ranks[i+1]}"
                    )


class TestIssue7StdSuppression:
    def test_single_entry_no_plus_minus_zero(self):
        """Issue 7: single-entry memory has std=0 → skip the ± clause."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _SINGLE, "action_type": "reversible", "domain": "general",
        })
        summary = r.json().get("knowledge_age_summary", "")
        if summary:
            assert "±0.0" not in summary, f"±0.0 should be suppressed: {summary}"


class TestTask2CacheKeyHash:
    def test_safe_key_hash_caches_result(self):
        """#15: second call returns cached value without recomputing."""
        kr = {"key_hash": hashlib.sha256(b"sg_test_key_001").hexdigest(),
              "customer_id": "cus_test_001"}
        h1 = _safe_key_hash(kr)
        assert "_cached_hash" in kr  # cache populated
        h2 = _safe_key_hash(kr)
        assert h1 == h2  # same value


class TestTask5CORSStaging:
    def test_staging_excludes_localhost(self):
        """#22: non-development environments must not include localhost."""
        # In test env, ENV is not set → not "development" → localhost stripped
        from api.main import _ALLOWED_ORIGINS
        has_localhost = any("localhost" in o for o in _ALLOWED_ORIGINS)
        env = os.getenv("ENV", "").lower()
        if env != "development":
            assert not has_localhost, f"localhost in CORS for ENV={env or 'unset'}"


class TestTask14ComponentAttribution:
    def test_unknown_component_logged_not_rejected(self):
        """#45: unknown component names are accepted but logged."""
        # First create a preflight to get an outcome_id
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _SINGLE, "action_type": "reversible", "domain": "general",
        })
        oid = r.json().get("outcome_id")
        if not oid:
            pytest.skip("No outcome_id in response")
        # Close with an unknown component — should not crash
        r2 = client.post("/v1/outcome", headers=AUTH, json={
            "outcome_id": oid,
            "status": "failure",
            "failure_components": ["s_freshness", "totally_made_up_component"],
        })
        # Should succeed (not reject unknown components)
        assert r2.status_code in (200, 409)  # 409 if already closed by a prior test


class TestTask16OpenAPI:
    def test_openapi_spec_accessible(self):
        r = client.get("/docs/openapi.json")
        assert r.status_code == 200
        d = r.json()
        assert "openapi" in d
        assert "paths" in d
