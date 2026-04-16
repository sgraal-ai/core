"""Tests for three endpoints/features shipped in this sprint:
 - Task 2: GET /v1/compliance/nist-ai-rmf
 - Task 3: governance_score + GET /v1/governance-score/{agent_id}
 - Task 4: thermodynamic_cost field + BLOCK audit extras.
"""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


_HEALTHY = [{
    "id": "m1", "content": "fresh pref", "type": "preference",
    "timestamp_age_days": 1, "source_trust": 0.95, "source_conflict": 0.05, "downstream_count": 1,
}]

_STALE = [{
    "id": "m1", "content": "stale", "type": "tool_state",
    "timestamp_age_days": 120, "source_trust": 0.25, "source_conflict": 0.75, "downstream_count": 8,
}]


# ---- Task 2: NIST AI RMF ----
class TestNistAiRmf:
    def test_nist_endpoint_public_no_auth(self):
        r = client.get("/v1/compliance/nist-ai-rmf")
        assert r.status_code == 200
        d = r.json()
        assert d["framework"] == "NIST AI RMF 1.0"
        assert set(d["functions"].keys()) == {"GOVERN", "MAP", "MEASURE", "MANAGE"}

    def test_nist_endpoint_has_all_functions_populated(self):
        r = client.get("/v1/compliance/nist-ai-rmf")
        d = r.json()
        for func_name, func_body in d["functions"].items():
            assert "description" in func_body
            assert "controls" in func_body
            assert len(func_body["controls"]) >= 3
            for ctrl in func_body["controls"]:
                assert {"id", "name", "satisfied", "evidence", "endpoint"}.issubset(ctrl.keys())
                assert isinstance(ctrl["satisfied"], bool)

    def test_nist_summary_counts_match(self):
        r = client.get("/v1/compliance/nist-ai-rmf")
        d = r.json()
        total = sum(len(f["controls"]) for f in d["functions"].values())
        assert d["summary"]["total_controls_mapped"] == total


# ---- Task 3: Governance Score ----
class TestGovernanceScore:
    def test_governance_score_on_preflight_response(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _HEALTHY, "action_type": "reversible", "domain": "general",
        })
        assert r.status_code == 200
        d = r.json()
        assert "governance_score" in d
        gs = d["governance_score"]
        assert 0.0 <= gs <= 100.0
        assert "governance_score_components" in d
        comps = d["governance_score_components"]
        assert set(comps["weights"].keys()) == {"omega", "fleet_health", "stability", "monoculture", "calibration"}

    def test_governance_score_healthier_memory_scores_higher(self):
        r1 = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _HEALTHY, "action_type": "reversible", "domain": "general",
        })
        r2 = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _STALE, "action_type": "irreversible", "domain": "fintech",
        })
        assert r1.status_code == 200 and r2.status_code == 200
        # Healthy memory should have higher governance than stale memory
        assert r1.json()["governance_score"] > r2.json()["governance_score"]

    def test_governance_score_history_endpoint(self):
        # In test env, the supabase table is empty — endpoint should still respond 200
        r = client.get("/v1/governance-score/agent_test_001", headers=AUTH)
        assert r.status_code == 200
        d = r.json()
        assert d["agent_id"] == "agent_test_001"
        assert "count" in d
        assert "history" in d
        # Either real history or empty-with-note fallback
        assert isinstance(d["history"], list)
        if d["count"] == 0:
            assert "note" in d


# ---- Task 4: Thermodynamic cost ----
class TestThermodynamicCost:
    def test_thermodynamic_cost_on_every_response(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _HEALTHY, "action_type": "reversible", "domain": "general",
        })
        assert r.status_code == 200
        d = r.json()
        assert "thermodynamic_cost" in d
        tc = d["thermodynamic_cost"]
        assert {"bits_erased", "landauer_joules", "temperature_kelvin", "method"}.issubset(tc.keys())
        assert tc["bits_erased"] > 0
        assert tc["landauer_joules"] > 0
        assert tc["temperature_kelvin"] == 300

    def test_thermodynamic_cost_scales_with_entry_count(self):
        r1 = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _HEALTHY, "action_type": "reversible", "domain": "general",
        })
        r2 = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _HEALTHY * 5, "action_type": "reversible", "domain": "general",
        })
        tc1 = r1.json()["thermodynamic_cost"]
        tc2 = r2.json()["thermodynamic_cost"]
        # 5x entries → 5x bits erased and 5x joules
        assert tc2["bits_erased"] == tc1["bits_erased"] * 5
        assert abs(tc2["landauer_joules"] - tc1["landauer_joules"] * 5) < 1e-20

    def test_thermodynamic_cost_formula_is_landauer_bound(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _HEALTHY, "action_type": "reversible", "domain": "general",
        })
        tc = r.json()["thermodynamic_cost"]
        # Verify E = k * T * ln(2) * bits = 2.87e-21 * bits
        expected = tc["bits_erased"] * 2.87e-21
        assert abs(tc["landauer_joules"] - expected) < 1e-25
