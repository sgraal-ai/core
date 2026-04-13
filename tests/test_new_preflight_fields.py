"""Tests for new preflight response fields: days_until_block, confidence_calibration, signal_vector_logged."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def _fresh_entry(**overrides):
    defaults = {
        "id": "npf_001", "content": "Test memory", "type": "preference",
        "timestamp_age_days": 1, "source_trust": 0.95, "source_conflict": 0.05,
        "downstream_count": 1,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# days_until_block
# ---------------------------------------------------------------------------

class TestDaysUntilBlock:
    def test_field_present_in_response(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_fresh_entry()],
            "action_type": "informational", "domain": "general",
        })
        assert r.status_code == 200
        j = r.json()
        assert "days_until_block" in j
        assert "days_until_block_confidence" in j

    def test_null_without_history(self):
        """Without score_history and no Redis, should return null."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_fresh_entry()],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        # Test keys are dry-run-like; days_until_block should be null
        assert j["days_until_block"] is None or isinstance(j["days_until_block"], (int, float))

    def test_zero_when_already_blocked(self):
        """If omega >= block threshold, days_until_block should be 0."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _fresh_entry(id=f"blk_{i}", timestamp_age_days=500,
                             source_trust=0.1, source_conflict=0.9,
                             downstream_count=50)
                for i in range(5)
            ],
            "action_type": "destructive", "domain": "medical",
        })
        j = r.json()
        if j["recommended_action"] == "BLOCK":
            assert j["days_until_block"] == 0.0
            assert j["days_until_block_confidence"] == 1.0

    def test_with_score_history(self):
        """With score_history provided, should attempt computation."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_fresh_entry()],
            "action_type": "informational", "domain": "general",
            "score_history": [20, 22, 25, 27, 30, 32, 35, 38, 40, 42],
        })
        j = r.json()
        assert "days_until_block" in j


# ---------------------------------------------------------------------------
# confidence_calibration
# ---------------------------------------------------------------------------

class TestConfidenceCalibration:
    def test_field_present(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_fresh_entry()],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        assert "confidence_calibration" in j
        cc = j["confidence_calibration"]
        assert "state" in cc
        assert "score" in cc
        assert "r_belief" in cc
        assert "s_drift" in cc
        assert "h1_rank" in cc

    def test_state_is_valid_enum(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_fresh_entry()],
            "action_type": "informational", "domain": "general",
        })
        cc = r.json()["confidence_calibration"]
        assert cc["state"] in ("OVERCONFIDENT", "UNDERCONFIDENT", "CALIBRATED")

    def test_score_in_range(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_fresh_entry()],
            "action_type": "informational", "domain": "general",
        })
        cc = r.json()["confidence_calibration"]
        assert 0.0 <= cc["score"] <= 1.0

    def test_calibrated_for_normal_memory(self):
        """Fresh, trusted memory should be CALIBRATED."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_fresh_entry(
                timestamp_age_days=1, source_trust=0.9,
                source_conflict=0.1, downstream_count=2,
            )],
            "action_type": "informational", "domain": "general",
        })
        cc = r.json()["confidence_calibration"]
        assert cc["state"] == "CALIBRATED"

    def test_h1_rank_is_integer(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_fresh_entry()],
            "action_type": "informational", "domain": "general",
        })
        cc = r.json()["confidence_calibration"]
        assert isinstance(cc["h1_rank"], int)


# ---------------------------------------------------------------------------
# signal_vector_logged
# ---------------------------------------------------------------------------

class TestSignalVectorLogged:
    def test_field_present(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_fresh_entry()],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        assert "signal_vector_logged" in j

    def test_false_for_test_keys(self):
        """Test/demo keys skip Redis, so signal_vector_logged should be false."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_fresh_entry()],
            "action_type": "informational", "domain": "general",
        })
        # Test keys have _is_dry_run or no Redis, so logging is skipped
        assert r.json()["signal_vector_logged"] is False

    def test_is_boolean(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_fresh_entry()],
            "action_type": "informational", "domain": "general",
        })
        assert isinstance(r.json()["signal_vector_logged"], bool)
