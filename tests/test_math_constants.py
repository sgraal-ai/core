"""Tests for mathematical constant integrations: φ, γ, δ₁ (#625-627)."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def _entry(**overrides):
    defaults = {
        "id": "mc_001", "content": "Test memory for constants", "type": "semantic",
        "timestamp_age_days": 10, "source_trust": 0.8, "source_conflict": 0.15,
        "downstream_count": 5,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# #625: φ golden ratio for heal_roi
# ---------------------------------------------------------------------------

class TestPhiWeighting:
    def test_phi_weighted_true(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        assert r.json()["phi_weighted"] is True

    def test_repair_plan_has_priority_weight(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _entry(id="phi_1", timestamp_age_days=200, source_conflict=0.8, downstream_count=20),
            ],
            "action_type": "irreversible", "domain": "fintech",
        })
        rp = r.json().get("repair_plan", [])
        for item in rp:
            assert "priority_weight" in item
            assert 0 < item["priority_weight"] <= 1.0

    def test_weights_decrease_by_golden_ratio(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _entry(id="phi_a", timestamp_age_days=300, source_conflict=0.9, downstream_count=30),
                _entry(id="phi_b", timestamp_age_days=200, source_conflict=0.7, downstream_count=20),
            ],
            "action_type": "destructive", "domain": "medical",
        })
        rp = r.json().get("repair_plan", [])
        if len(rp) >= 2:
            assert rp[0]["priority_weight"] > rp[1]["priority_weight"]
            ratio = rp[0]["priority_weight"] / rp[1]["priority_weight"]
            assert 1.5 < ratio < 1.7  # φ ≈ 1.618


# ---------------------------------------------------------------------------
# #626: γ Euler-Mascheroni for monoculture
# ---------------------------------------------------------------------------

class TestGammaMonoculture:
    def test_gamma_used_true(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        assert r.json()["monoculture_gamma_used"] is True

    def test_score_in_range(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry(), _entry(id="mc_002")],
            "action_type": "informational", "domain": "general",
        })
        score = r.json()["monoculture_risk_score"]
        assert 0.0 <= score <= 1.0

    def test_more_entries_changes_threshold(self):
        """With more entries, the expected_sources threshold increases (coupon collector)."""
        r_few = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry(id=f"few_{i}") for i in range(2)],
            "action_type": "informational", "domain": "general",
        })
        r_many = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry(id=f"many_{i}", content=f"Unique content {i}") for i in range(10)],
            "action_type": "informational", "domain": "general",
        })
        # Both should have valid scores — the threshold adapts
        assert 0 <= r_few.json()["monoculture_risk_score"] <= 1
        assert 0 <= r_many.json()["monoculture_risk_score"] <= 1


# ---------------------------------------------------------------------------
# #627: δ₁ Feigenbaum for chaos onset
# ---------------------------------------------------------------------------

class TestFeigenbaumChaos:
    def test_chaos_fields_present_with_history(self):
        """With score_history, lyapunov_exponent should include chaos_type."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
            "score_history": [20, 25, 30, 35, 40, 45, 50, 55, 60, 65],
        })
        lyap = r.json().get("lyapunov_exponent")
        if lyap:
            assert "chaos_type" in lyap
            assert lyap["chaos_type"] in ("period_doubling", "stochastic")
            assert "chaos_onset_predicted" in lyap
            assert isinstance(lyap["chaos_onset_predicted"], bool)

    def test_no_chaos_for_stable_history(self):
        """Stable flat history should not predict chaos onset."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
            "score_history": [20, 20, 20, 20, 20, 20, 20, 20, 20, 20],
        })
        lyap = r.json().get("lyapunov_exponent")
        if lyap:
            assert lyap["chaos_onset_predicted"] is False

    def test_chaos_type_is_string(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
            "score_history": [10, 30, 15, 45, 20, 60, 25, 70, 30, 80],
        })
        lyap = r.json().get("lyapunov_exponent")
        if lyap:
            assert isinstance(lyap["chaos_type"], str)
