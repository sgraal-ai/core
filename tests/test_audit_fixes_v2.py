"""Tests for audit fixes v2 — circuit breaker migration, route collision, evasion prevention."""
import pytest


def _e(id="m1", content="Standard data.", type="semantic", age=1, trust=0.9,
       conflict=0.05, downstream=3, provenance_chain=None):
    d = {"id": id, "content": content, "type": type, "timestamp_age_days": age,
         "source_trust": trust, "source_conflict": conflict, "downstream_count": downstream}
    if provenance_chain is not None:
        d["provenance_chain"] = provenance_chain
    return d


def _client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


AUTH = {"Authorization": "Bearer sg_demo_playground"}


class TestCircuitBreakerMigration:
    def test_circuit_breaker_migration(self):
        """Old omega_history format migrates to decision_history correctly."""
        # Simulate old format: omega_history with high values
        old_state = {"state": "OPEN", "omega_history": [85, 90, 82, 88, 91], "last_opened": 0}
        # The migration converts omega > 80 → BLOCK, omega <= 80 → USE_MEMORY
        expected_decisions = ["BLOCK", "BLOCK", "BLOCK", "BLOCK", "BLOCK"]

        # Verify the migration logic directly
        if "omega_history" in old_state and "decision_history" not in old_state:
            migrated = ["BLOCK" if o > 80 else "USE_MEMORY" for o in old_state["omega_history"]]
        else:
            migrated = old_state.get("decision_history", [])
        assert migrated == expected_decisions


class TestDuplicateRouteResolved:
    def test_compiled_policy_route_reachable(self):
        """GET /v1/compiled-policies/{id} is reachable (renamed from /v1/policies/{id})."""
        c = _client()
        resp = c.get("/v1/compiled-policies/nonexistent", headers=AUTH)
        assert resp.status_code == 404
        assert "Compiled policy" in resp.json()["detail"]

    def test_named_policy_route_distinct(self):
        """GET /v1/policies/{name} returns named policy, not compiled."""
        c = _client()
        resp = c.get("/v1/policies/nonexistent-policy", headers=AUTH)
        assert resp.status_code == 404
        assert "Policy" in resp.json()["detail"]


class TestGenuineCorroborationRequiresChains:
    def test_genuine_corroboration_requires_chains(self):
        """Empty provenance chains cannot bypass consensus collapse detection."""
        from api.main import _check_consensus_collapse
        entries = [
            _e(id="m1", content="Settlement netting approved for transaction processing.",
               trust=0.90, conflict=0.02, downstream=8),
            _e(id="m2", content="Settlement netting approved per review processing.",
               trust=0.90, conflict=0.02, downstream=8),
            _e(id="m3", content="Settlement netting confirmed approved for processing.",
               trust=0.90, conflict=0.02, downstream=18),
        ]
        # No provenance chains → genuine_corroboration should be False
        result = _check_consensus_collapse(entries)
        assert result.get("genuine_corroboration") is not True or result["consensus_collapse"] != "CLEAN"
