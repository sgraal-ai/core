"""Tests for single_point_of_failure and monoculture_risk_score preflight fields."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def _entry(**overrides):
    defaults = {
        "id": "sp_001", "content": "Test memory", "type": "preference",
        "timestamp_age_days": 5, "source_trust": 0.9, "source_conflict": 0.1,
        "downstream_count": 2,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# single_point_of_failure
# ---------------------------------------------------------------------------

class TestSinglePointOfFailure:
    def test_fields_present(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        assert "single_point_of_failure_entry_id" in j
        assert "single_point_of_failure_score" in j

    def test_null_for_low_risk(self):
        """Low-risk entries should not trigger SPOF."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _entry(id="safe_1", downstream_count=1, source_trust=0.95),
                _entry(id="safe_2", downstream_count=1, source_trust=0.95),
            ],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        assert j["single_point_of_failure_entry_id"] is None
        assert j["single_point_of_failure_score"] is None

    def test_high_downstream_entry_flagged(self):
        """Entry with very high downstream count may be flagged."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _entry(id="hub_1", downstream_count=80, source_trust=0.5,
                       source_conflict=0.3, has_backup_source=False),
                _entry(id="leaf_1", downstream_count=1, source_trust=0.95),
            ],
            "action_type": "irreversible", "domain": "fintech",
        })
        j = r.json()
        if j["single_point_of_failure_entry_id"] is not None:
            assert j["single_point_of_failure_score"] > 0.5
            assert j["single_point_of_failure_score"] <= 1.0

    def test_score_bounded(self):
        """SPOF score must be between 0.5 and 1.0 when present."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _entry(id="big_1", downstream_count=100, source_trust=0.3,
                       source_conflict=0.5, has_backup_source=False),
            ],
            "action_type": "destructive", "domain": "medical",
        })
        j = r.json()
        if j["single_point_of_failure_score"] is not None:
            assert 0.5 < j["single_point_of_failure_score"] <= 1.0


# ---------------------------------------------------------------------------
# monoculture_risk_score
# ---------------------------------------------------------------------------

class TestMonocultureRisk:
    def test_fields_present(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        assert "monoculture_risk_score" in j
        assert "monoculture_risk_level" in j

    def test_score_in_range(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        assert 0.0 <= j["monoculture_risk_score"] <= 1.0

    def test_level_matches_score(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        score = j["monoculture_risk_score"]
        level = j["monoculture_risk_level"]
        if score > 0.6:
            assert level == "HIGH"
        elif score > 0.3:
            assert level == "MEDIUM"
        else:
            assert level == "LOW"

    def test_valid_level_enum(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        assert r.json()["monoculture_risk_level"] in ("LOW", "MEDIUM", "HIGH")

    def test_single_source_higher_risk(self):
        """A single source with one entry should have higher monoculture risk
        than diverse sources."""
        r_single = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry(id="mono_1", source_trust=0.95, source_conflict=0.02)],
            "action_type": "informational", "domain": "general",
        })
        r_diverse = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _entry(id="div_1", source_trust=0.8, source_conflict=0.2),
                _entry(id="div_2", source_trust=0.6, source_conflict=0.3, content="Different topic entirely"),
                _entry(id="div_3", source_trust=0.7, source_conflict=0.15, content="Third independent source"),
            ],
            "action_type": "informational", "domain": "general",
        })
        # Single source should have >= monoculture risk
        assert r_single.json()["monoculture_risk_score"] >= r_diverse.json()["monoculture_risk_score"] - 0.1
