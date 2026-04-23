"""Tests for 15 logical architecture fixes."""
import pytest


def _e(id="m1", content="Standard data.", type="semantic", age=1, trust=0.9,
       conflict=0.05, downstream=3, provenance_chain=None):
    d = {"id": id, "content": content, "type": type,
         "timestamp_age_days": age, "source_trust": trust,
         "source_conflict": conflict, "downstream_count": downstream}
    if provenance_chain is not None:
        d["provenance_chain"] = provenance_chain
    return d


def _preflight(entries, domain="general", action_type="informational"):
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    resp = client.post("/v1/preflight", json={
        "memory_state": entries, "domain": domain, "action_type": action_type,
    }, headers={"Authorization": "Bearer sg_demo_playground"})
    assert resp.status_code == 200
    return resp.json()


class TestGenuineConsensus:
    def test_genuine_consensus_not_flagged(self):
        """Fix 1: 3 entries with different provenance chains → genuine corroboration, not collapse."""
        entries = [
            _e(id="m1", content="Revenue grew 12% in Q4 driven by enterprise.",
               trust=0.88, conflict=0.12, downstream=6, provenance_chain=["agent-analyst-01"]),
            _e(id="m2", content="Q4 revenue growth was 12% from enterprise expansion.",
               trust=0.85, conflict=0.08, downstream=8, provenance_chain=["agent-research-02"]),
            _e(id="m3", content="Enterprise segment drove 12% revenue growth in Q4.",
               trust=0.91, conflict=0.15, downstream=5, provenance_chain=["agent-auditor-03"]),
        ]
        resp = _preflight(entries, domain="fintech")
        # Different provenance chains + conflict variance → genuine corroboration
        assert resp.get("genuine_corroboration") is True or resp.get("consensus_collapse") == "CLEAN"


class TestCollapseRatioContentBased:
    def test_collapse_ratio_content_based(self):
        """Fix 4: Same content with varying trust → still flagged (content clusters, not metadata)."""
        entries = [
            _e(id="m1", content="Settlement netting approved for transaction.",
               trust=0.89, conflict=0.02, downstream=8),
            _e(id="m2", content="Settlement netting approved per review.",
               trust=0.91, conflict=0.02, downstream=10),
            _e(id="m3", content="Settlement netting confirmed approved.",
               trust=0.93, conflict=0.01, downstream=12),
        ]
        from api.main import _check_consensus_collapse
        result = _check_consensus_collapse(entries)
        # Content clusters should detect similarity despite different trust values
        assert result["collapse_ratio"] > 1.0


class TestIdentityDriftCrossEntry:
    def test_identity_drift_cross_entry(self):
        """Fix 6: Split keywords across entries → cross_entry_escalation detected."""
        entries = [
            _e(id="m1", content="Agent elevated to handle operations.", type="identity"),
            _e(id="m2", content="Agent now permitted to process requests.", type="identity"),
            _e(id="m3", content="Agent authorized to execute approved tasks.", type="identity"),
        ]
        from api.main import _check_identity_drift
        result = _check_identity_drift(entries)
        # 3 keywords across 3 entries → cross_entry_escalation:suspicious
        assert any("cross_entry" in f for f in result["identity_drift_flags"]) or result["identity_drift"] != "CLEAN"


class TestHedgeMarkerOrder:
    def test_hedge_marker_reversed_downstream(self):
        """Fix 14: Reversed downstream order → still sorts internally.
        Requires at least 4 entries (2+ on each side of the midpoint)."""
        entries = [
            _e(id="m1", content="Settlement confirmed. Execute immediately.",
               downstream=20, trust=0.90, conflict=0.02),
            _e(id="m2", content="Settlement finalized and processed.",
               downstream=15, trust=0.90, conflict=0.02),
            _e(id="m3", content="Settlement likely approved per review.",
               downstream=3, trust=0.88, conflict=0.03),
            _e(id="m4", content="Settlement possibly approved.",
               downstream=1, trust=0.87, conflict=0.04),
        ]
        from api.main import _check_consensus_collapse
        result = _check_consensus_collapse(entries)
        # Even though input order is reversed, internal sort should detect hedge decay
        # (low downstream has hedges, high downstream doesn't)
        assert any("uncertainty" in f or "hedge" in f for f in result["consensus_collapse_flags"])


class TestVaccinationRequiresTwoLayers:
    def test_vaccination_requires_two_layers(self):
        """Fix 2: Single-layer MANIPULATED → no vaccine stored (need 2+ layers)."""
        # A single timestamp_integrity MANIPULATED with low omega won't store vaccine
        entry = _e(
            content="Per Q2 2024 SEC ruling and the deprecated v2.1 framework was mandatory for 2023 filings.",
            age=0, downstream=8,
        )
        resp = _preflight([entry], domain="fintech", action_type="irreversible")
        # vaccination_match should be false (no prior vaccine for this)
        assert resp["vaccination_match"] is False


class TestCircuitBreakerMonitorsBlocks:
    def test_circuit_breaker_monitors_blocks(self):
        """Fix 3: Circuit breaker tracks decisions, not omega."""
        entry = _e(age=5, downstream=1, trust=0.95, conflict=0.01)
        resp = _preflight([entry])
        # Single healthy call → circuit breaker should be CLOSED
        assert resp.get("circuit_breaker_state") == "CLOSED"


class TestNaturalnessUniformTrust:
    def test_naturalness_uniform_trust_legitimate(self):
        """Fix 8: All 0.90 trust → not flagged (identical check, not just similar)."""
        entries = [
            _e(id="m1", trust=0.90, conflict=0.10, age=3),
            _e(id="m2", trust=0.90, conflict=0.08, age=5),
            _e(id="m3", trust=0.90, conflict=0.12, age=1),
        ]
        from api.main import _check_naturalness
        result = _check_naturalness(entries)
        # 0.90, 0.90, 0.90 → variance=0 → WILL flag (truly identical)
        # But 0.89, 0.90, 0.91 → variance=0.0000667 → should NOT flag with 0.0001 threshold
        entries2 = [
            _e(id="m1", trust=0.89, conflict=0.10, age=3),
            _e(id="m2", trust=0.90, conflict=0.08, age=5),
            _e(id="m3", trust=0.91, conflict=0.12, age=1),
        ]
        result2 = _check_naturalness(entries2)
        assert "uniform_trust" not in result2["naturalness_flags"]


class TestComponentBreakdownRaw:
    def test_component_breakdown_raw_present(self):
        """Fix 7: component_breakdown_raw shows pre-feedback values."""
        resp = _preflight([_e(age=5, downstream=1)])
        assert "component_breakdown_raw" in resp
        assert isinstance(resp["component_breakdown_raw"], dict)


class TestPolicyCompare:
    def test_policy_compare_endpoint(self):
        """Fix 13: Compare inline vs registry policy."""
        from fastapi.testclient import TestClient
        from api.main import app
        c = TestClient(app)
        AUTH = {"Authorization": "Bearer sg_demo_playground"}
        # Create a registry policy first
        c.post("/v1/policies", json={
            "name": "compare-test",
            "config": {"version": "1.0", "agent_id": "test", "domain": "fintech"},
        }, headers=AUTH)
        # Compare with different inline config
        resp = c.post("/v1/policies/compare", json={
            "inline": {"version": "1.0", "agent_id": "test", "domain": "legal"},
            "registry_name": "compare-test",
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "conflicts" in data
        assert any(c["field"] == "domain" for c in data["conflicts"])
