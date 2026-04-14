"""Tests for decision-entropy, module-health, and temporal-patterns analytics endpoints."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app, _outcomes, _outcome_set
import time

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def _seed_outcomes(agent_id, decisions, domain="general"):
    """Seed outcomes with a sequence of decisions for testing."""
    for i, dec in enumerate(decisions):
        oid = f"anal_{agent_id}_{i}_{int(time.time()*1000)}"
        _outcome_set(oid, {
            "request_id": oid,
            "agent_id": agent_id,
            "status": "open",
            "omega_mem_final": {"USE_MEMORY": 10, "WARN": 35, "ASK_USER": 55, "BLOCK": 80}.get(dec, 20),
            "recommended_action": dec,
            "component_breakdown": {"s_freshness": 20, "s_drift": 15, "s_provenance": 10,
                                    "s_propagation": 8, "r_recall": 25, "r_encode": 12,
                                    "s_interference": 5, "s_recovery": 40, "r_belief": 30, "s_relevance": 3},
            "domain": domain,
            "_ts": time.time() - (len(decisions) - i) * 60,
        })


# ---------------------------------------------------------------------------
# Decision Entropy
# ---------------------------------------------------------------------------

class TestDecisionEntropy:
    def test_requires_agent_id(self):
        r = client.get("/v1/analytics/decision-entropy", headers=AUTH)
        assert r.status_code == 400

    def test_requires_auth(self):
        r = client.get("/v1/analytics/decision-entropy?agent_id=test")
        assert r.status_code in (401, 403)

    def test_insufficient_data(self):
        r = client.get("/v1/analytics/decision-entropy?agent_id=nonexistent_agent_xyz", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["sample_size"] < 2

    def test_with_seeded_data(self):
        _seed_outcomes("entropy-test-1", ["USE_MEMORY"] * 5 + ["WARN"] * 3 + ["BLOCK"] * 2)
        r = client.get("/v1/analytics/decision-entropy?agent_id=entropy-test-1", headers=AUTH)
        j = r.json()
        assert j["sample_size"] >= 10
        assert 0 <= j["decision_entropy"] <= 2.0
        assert j["entropy_level"] in ("LOW", "MEDIUM", "HIGH")
        assert "transition_matrix" in j
        assert j["most_common_decision"] == "USE_MEMORY"

    def test_low_entropy_for_uniform_agent(self):
        _seed_outcomes("entropy-test-2", ["USE_MEMORY"] * 20)
        r = client.get("/v1/analytics/decision-entropy?agent_id=entropy-test-2", headers=AUTH)
        j = r.json()
        assert j["decision_entropy"] == 0.0
        assert j["entropy_level"] == "LOW"

    def test_transition_matrix_structure(self):
        _seed_outcomes("entropy-test-3", ["USE_MEMORY", "WARN", "USE_MEMORY", "BLOCK", "WARN"])
        r = client.get("/v1/analytics/decision-entropy?agent_id=entropy-test-3", headers=AUTH)
        tm = r.json()["transition_matrix"]
        for src in ["USE_MEMORY", "WARN", "ASK_USER", "BLOCK"]:
            assert src in tm
            for dst in ["USE_MEMORY", "WARN", "ASK_USER", "BLOCK"]:
                assert dst in tm[src]


# ---------------------------------------------------------------------------
# Module Health
# ---------------------------------------------------------------------------

class TestModuleHealth:
    def test_returns_200(self):
        r = client.get("/v1/analytics/module-health", headers=AUTH)
        assert r.status_code == 200
        j = r.json()
        assert "modules" in j
        assert "total_calls" in j
        assert "inactive_modules" in j

    def test_requires_auth(self):
        r = client.get("/v1/analytics/module-health")
        assert r.status_code in (401, 403)

    def test_module_structure(self):
        # Seed some outcomes first
        _seed_outcomes("module-health-1", ["USE_MEMORY"] * 3)
        r = client.get("/v1/analytics/module-health", headers=AUTH)
        modules = r.json()["modules"]
        assert len(modules) >= 10  # 10 core components
        for m in modules:
            assert "module" in m
            assert "activation_rate" in m
            assert "null_rate" in m
            assert "mean_value" in m
            assert 0 <= m["activation_rate"] <= 1.0

    def test_generated_at_present(self):
        r = client.get("/v1/analytics/module-health", headers=AUTH)
        assert "generated_at" in r.json()


# ---------------------------------------------------------------------------
# Temporal Patterns
# ---------------------------------------------------------------------------

class TestTemporalPatterns:
    def test_returns_200(self):
        r = client.get("/v1/analytics/temporal-patterns", headers=AUTH)
        assert r.status_code == 200

    def test_requires_auth(self):
        r = client.get("/v1/analytics/temporal-patterns")
        assert r.status_code in (401, 403)

    def test_with_seeded_data(self):
        _seed_outcomes("temporal-test-1", ["USE_MEMORY"] * 5 + ["WARN"] * 3)
        r = client.get("/v1/analytics/temporal-patterns?days=1", headers=AUTH)
        j = r.json()
        assert "hourly_omega" in j or "total_calls" in j

    def test_insufficient_data_message(self):
        r = client.get("/v1/analytics/temporal-patterns?days=1", headers=AUTH)
        j = r.json()
        if j["total_calls"] < 3:
            assert j["pattern_detected"] is False

    def test_hour_range(self):
        _seed_outcomes("temporal-test-2", ["USE_MEMORY"] * 10)
        r = client.get("/v1/analytics/temporal-patterns?days=30", headers=AUTH)
        j = r.json()
        if j["total_calls"] >= 3:
            assert 0 <= j["peak_risk_hour"] <= 23
            assert 0 <= j["low_risk_hour"] <= 23
            assert isinstance(j["circadian_amplitude"], (int, float))
