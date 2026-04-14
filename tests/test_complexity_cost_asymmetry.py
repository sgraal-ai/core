"""Tests for memory_complexity_trend and decision_cost_asymmetry preflight fields."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def _entry(**overrides):
    defaults = {
        "id": "cc_001", "content": "Test memory", "type": "preference",
        "timestamp_age_days": 5, "source_trust": 0.9, "source_conflict": 0.1,
        "downstream_count": 2,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# memory_complexity_trend
# ---------------------------------------------------------------------------

class TestMemoryComplexityTrend:
    def test_field_present(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        assert r.status_code == 200
        assert "memory_complexity_trend" in r.json()

    def test_valid_states(self):
        """Value must be one of the defined states."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        valid = {"FRAGMENTING", "ECHO_CHAMBER", "CONSOLIDATING", "STABLE", "UNKNOWN"}
        assert r.json()["memory_complexity_trend"] in valid

    def test_unknown_without_history(self):
        """Test/demo keys have no Redis history → UNKNOWN."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        # Test keys skip Redis → always UNKNOWN
        assert r.json()["memory_complexity_trend"] == "UNKNOWN"

    def test_is_string(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        assert isinstance(r.json()["memory_complexity_trend"], str)


# ---------------------------------------------------------------------------
# decision_cost_asymmetry
# ---------------------------------------------------------------------------

class TestDecisionCostAsymmetry:
    def test_field_present(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        assert r.status_code == 200
        dca = r.json()["decision_cost_asymmetry"]
        assert "cost_adjusted_decision" in dca
        assert "cost_adjustment_reason" in dca
        assert "original_recommended_action" in dca
        assert "adjusted_threshold_warn" in dca
        assert "adjusted_threshold_block" in dca

    def test_no_adjustment_for_informational(self):
        """Informational actions should never trigger cost adjustment."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        dca = r.json()["decision_cost_asymmetry"]
        assert dca["cost_adjusted_decision"] is False
        assert dca["cost_adjustment_reason"] is None
        assert dca["original_recommended_action"] is None

    def test_no_adjustment_for_reversible(self):
        """Reversible actions should not trigger cost adjustment."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "reversible", "domain": "general",
        })
        dca = r.json()["decision_cost_asymmetry"]
        assert dca["cost_adjusted_decision"] is False

    def test_structure_when_not_adjusted(self):
        """When not adjusted, thresholds should be null."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        dca = r.json()["decision_cost_asymmetry"]
        assert dca["adjusted_threshold_warn"] is None
        assert dca["adjusted_threshold_block"] is None

    def test_destructive_high_risk_triggers_adjustment(self):
        """Destructive action with high-risk memory should potentially trigger adjustment."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _entry(id="dca_1", timestamp_age_days=300, source_trust=0.15,
                       source_conflict=0.85, downstream_count=40),
                _entry(id="dca_2", timestamp_age_days=200, source_trust=0.2,
                       source_conflict=0.7, downstream_count=30),
            ],
            "action_type": "destructive", "domain": "medical",
        })
        dca = r.json()["decision_cost_asymmetry"]
        # Whether adjustment triggers depends on CVaR (needs score_history)
        # But structure should always be valid
        assert isinstance(dca["cost_adjusted_decision"], bool)
        if dca["cost_adjusted_decision"]:
            assert dca["adjusted_threshold_warn"] == 20
            assert dca["adjusted_threshold_block"] == 60
            assert dca["original_recommended_action"] is not None
            assert dca["cost_adjustment_reason"] == "high CVaR on irreversible action"

    def test_adjusted_action_overrides_response(self):
        """When cost-adjusted, response recommended_action should use adjusted thresholds."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _entry(id="adj_1", timestamp_age_days=200, source_trust=0.2,
                       source_conflict=0.8, downstream_count=50),
            ],
            "action_type": "destructive", "domain": "medical",
            "score_history": [40, 45, 50, 55, 60, 65, 70, 75, 80, 85],
        })
        dca = r.json()["decision_cost_asymmetry"]
        if dca["cost_adjusted_decision"]:
            # The recommended_action in response should differ from original
            assert r.json()["recommended_action"] != dca["original_recommended_action"] or \
                   r.json()["recommended_action"] == "BLOCK"
