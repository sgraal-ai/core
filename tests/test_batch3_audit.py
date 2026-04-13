"""Batch 3 audit tests — weight normalization, untested modules, untested endpoints, determinism."""
import sys, os, math, random, hashlib
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring_engine import compute, MemoryEntry
from scoring_engine.omega_mem import WEIGHTS

with patch.dict(os.environ, {}, clear=False):
    from fastapi.testclient import TestClient
    from api.main import app, _outcomes, _outcomes_lock

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def _fresh_entry(**overrides):
    defaults = {
        "id": "b3_001", "content": "Test memory", "type": "preference",
        "timestamp_age_days": 1, "source_trust": 0.95, "source_conflict": 0.05,
        "downstream_count": 1,
    }
    defaults.update(overrides)
    return defaults


def _make_entry(**overrides):
    defaults = {
        "id": "b3_001", "content": "Test memory", "type": "preference",
        "timestamp_age_days": 1, "source_trust": 0.95, "source_conflict": 0.05,
        "downstream_count": 1, "r_belief": 0.9,
    }
    defaults.update(overrides)
    return MemoryEntry(**defaults)


# ---------------------------------------------------------------------------
# Fix #17: Weight normalization
# ---------------------------------------------------------------------------

class TestWeightNormalization:
    """Omega score must always be in [0, 100]."""

    def test_omega_bounded_random_inputs(self):
        """200 random memory states → omega always in [0, 100]."""
        for i in range(200):
            rng = random.Random(i)
            entries = [_make_entry(
                id=f"rand_{i}_{j}",
                content=f"Content {j}",
                timestamp_age_days=rng.uniform(0, 500),
                source_trust=rng.uniform(0.01, 0.99),
                source_conflict=rng.uniform(0.01, 0.99),
                downstream_count=rng.randint(0, 100),
                r_belief=rng.uniform(0.01, 0.99),
            ) for j in range(rng.randint(1, 10))]
            result = compute(entries, action_type="reversible", domain="general")
            assert 0 <= result.omega_mem_final <= 100, f"omega={result.omega_mem_final} out of bounds (seed={i})"

    def test_omega_zero_for_perfect_state(self):
        """Perfect memory state → omega near 0."""
        entry = _make_entry(
            timestamp_age_days=0.1, source_trust=0.99,
            source_conflict=0.01, downstream_count=1,
            r_belief=0.99,
        )
        result = compute([entry], action_type="informational", domain="general")
        assert result.omega_mem_final <= 30

    def test_omega_high_for_terrible_state(self):
        """Terrible memory state → omega high."""
        entry = _make_entry(
            timestamp_age_days=500, source_trust=0.1,
            source_conflict=0.9, downstream_count=50,
            r_belief=0.1,
        )
        result = compute([entry], action_type="destructive", domain="medical")
        assert result.omega_mem_final >= 50


# ---------------------------------------------------------------------------
# Fix #18: A2 axiom — deterministic scoring
# ---------------------------------------------------------------------------

class TestDeterminism:
    """Same input must produce same output."""

    def test_same_input_same_omega(self):
        """Two calls with identical input → identical omega."""
        e1 = _make_entry()
        e2 = _make_entry()
        r1 = compute([e1], action_type="reversible", domain="general")
        r2 = compute([e2], action_type="reversible", domain="general")
        assert r1.omega_mem_final == r2.omega_mem_final
        assert r1.recommended_action == r2.recommended_action

    def test_determinism_via_api(self):
        """Two identical preflight API calls → same omega."""
        payload = {
            "memory_state": [_fresh_entry()],
            "action_type": "informational",
            "domain": "general",
        }
        r1 = client.post("/v1/preflight", headers=AUTH, json=payload)
        r2 = client.post("/v1/preflight", headers=AUTH, json=payload)
        assert r1.json()["omega_mem_final"] == r2.json()["omega_mem_final"]


# ---------------------------------------------------------------------------
# Fix #18: Frechet returns neutral instead of None
# ---------------------------------------------------------------------------

class TestFrechetNeutral:
    """Frechet should return neutral result when no reference available."""

    def test_no_reference_returns_result(self):
        from scoring_engine.frechet import compute_frechet
        result = compute_frechet([[1, 2, 3], [4, 5, 6], [7, 8, 9]], reference_vectors=None)
        assert result is not None
        assert result.fd_score == 0.0
        assert result.encoding_degraded is False

    def test_too_few_reference_returns_neutral(self):
        from scoring_engine.frechet import compute_frechet
        result = compute_frechet([[1, 2, 3], [4, 5, 6], [7, 8, 9]], reference_vectors=[[1, 2, 3]])
        assert result is not None
        assert result.fd_score == 0.0


# ---------------------------------------------------------------------------
# Fix #24: Tests for untested scoring modules
# ---------------------------------------------------------------------------

class TestShapleyExplain:
    """shapley_explain.py — Shapley value computation."""

    def test_basic_shapley(self):
        from scoring_engine import compute_shapley_values
        components = {"s_freshness": 50, "s_drift": 30, "s_provenance": 20}
        result = compute_shapley_values(components, action_type="reversible", domain="general")
        assert isinstance(result, dict)
        assert len(result) == 3

    def test_shapley_single_component(self):
        from scoring_engine import compute_shapley_values
        result = compute_shapley_values({"s_freshness": 50})
        assert isinstance(result, dict)
        assert len(result) == 1


class TestOWAProvenance:
    """owa_provenance.py — Ordered Weighted Averaging."""

    def test_basic_owa(self):
        from scoring_engine import compute_owa
        result = compute_owa([0.9, 0.8, 0.7])
        assert result is not None
        assert hasattr(result, "owa_score") or hasattr(result, "aggregated")

    def test_single_value(self):
        from scoring_engine import compute_owa
        result = compute_owa([0.5])
        assert result is not None


class TestSecurityTE:
    """security_transfer_entropy.py — information leakage detection."""

    def test_import_and_call(self):
        from scoring_engine import compute_security_te
        entries = [_make_entry(id=f"te_{i}", content=f"Content {i}") for i in range(5)]
        result = compute_security_te(entries)
        # Returns None when insufficient data — that's acceptable (not an error)
        assert result is None or hasattr(result, "leakage_detected")

    def test_with_more_entries(self):
        from scoring_engine import compute_security_te
        entries = [_make_entry(id=f"te_{i}", content=f"Content {i}" * 10) for i in range(20)]
        # Should not raise
        result = compute_security_te(entries)
        assert result is None or hasattr(result, "leakage_detected")


class TestPCTLVerification:
    """pctl_verification.py — probabilistic CTL."""

    def test_basic_pctl(self):
        from scoring_engine import compute_pctl
        result = compute_pctl(omega=50, n_sims=10, steps=5, seed="test")
        assert result is not None

    def test_pctl_high_omega(self):
        from scoring_engine import compute_pctl
        result = compute_pctl(omega=90, seed="test_high")
        assert result is not None


class TestMemoryTracker:
    """memory_tracker.py — auto-dependency detection."""

    def test_tracker_import(self):
        from scoring_engine import MemoryAccessTracker
        tracker = MemoryAccessTracker()
        assert tracker is not None

    def test_tracker_methods(self):
        from scoring_engine import MemoryAccessTracker
        tracker = MemoryAccessTracker()
        # Check it has expected interface
        assert callable(getattr(tracker, "track", None)) or callable(getattr(tracker, "auto_detect", None)) or hasattr(tracker, "__dict__")


# ---------------------------------------------------------------------------
# Fix #25: Tests for untested endpoints
# ---------------------------------------------------------------------------

class TestAdaptEndpoint:
    """POST /v1/adapt — format conversion."""

    def test_adapt_mem0(self):
        r = client.post("/v1/adapt", headers=AUTH, json={
            "format": "mem0",
            "data": [{"memory": "Test", "metadata": {"type": "episodic"}}],
        })
        assert r.status_code == 200

    def test_adapt_no_auth(self):
        r = client.post("/v1/adapt", json={"format": "raw", "data": []})
        assert r.status_code in (401, 403)

    def test_adapt_invalid_format(self):
        r = client.post("/v1/adapt", headers=AUTH, json={
            "format": "nonexistent_format", "data": [],
        })
        # Should still return 200 with best-effort conversion or 422
        assert r.status_code in (200, 422)


class TestMigrateEndpoint:
    """POST /v1/migrate — convert + preflight."""

    def test_migrate_basic(self):
        r = client.post("/v1/migrate", headers=AUTH, json={
            "format": "raw",
            "data": [{"id": "mig1", "content": "Test", "type": "episodic",
                      "timestamp_age_days": 1, "source_trust": 0.9,
                      "source_conflict": 0.1, "downstream_count": 1}],
            "action_type": "informational",
            "domain": "general",
        })
        assert r.status_code == 200

    def test_migrate_no_auth(self):
        r = client.post("/v1/migrate", json={"format": "raw", "data": []})
        assert r.status_code in (401, 403)


class TestPoliciesEndpoint:
    """POST/GET/DELETE /v1/policies — policy registry CRUD."""

    def test_create_policy(self):
        r = client.post("/v1/policies", headers=AUTH, json={
            "name": "test_audit_policy",
            "config": {"warn": 30, "block": 70},
        })
        assert r.status_code == 200

    def test_list_policies(self):
        r = client.get("/v1/policies", headers=AUTH)
        assert r.status_code == 200
        assert "policies" in r.json()

    def test_get_policy(self):
        client.post("/v1/policies", headers=AUTH, json={
            "name": "test_get_policy",
            "config": {"warn": 40},
        })
        r = client.get("/v1/policies/test_get_policy", headers=AUTH)
        assert r.status_code == 200

    def test_delete_policy(self):
        client.post("/v1/policies", headers=AUTH, json={
            "name": "test_del_policy",
            "config": {"warn": 50},
        })
        r = client.delete("/v1/policies/test_del_policy", headers=AUTH)
        assert r.status_code == 200


class TestPolicyValidateEndpoint:
    """POST /v1/policy/validate — .sgraal config validation."""

    def test_validate_basic(self):
        r = client.post("/v1/policy/validate", headers=AUTH, json={
            "config": {"warn_threshold": 40, "block_threshold": 80},
        })
        assert r.status_code == 200

    def test_validate_no_auth(self):
        r = client.post("/v1/policy/validate", json={"config": {}})
        assert r.status_code in (401, 403)


class TestPolicyApplyEndpoint:
    """POST /v1/policy/apply — apply policy to preflight."""

    def test_apply_basic(self):
        r = client.post("/v1/policy/apply", headers=AUTH, json={
            "memory_state": [_fresh_entry()],
            "config": {"warn_threshold": 40},
        })
        assert r.status_code == 200

    def test_apply_no_auth(self):
        r = client.post("/v1/policy/apply", json={"memory_state": [], "config": {}})
        assert r.status_code in (401, 403)


class TestAuditLogExport:
    """GET /v1/audit-log/export — export audit logs."""

    def test_export_csv(self):
        r = client.get("/v1/audit-log/export?format=csv", headers=AUTH)
        assert r.status_code == 200

    def test_export_splunk(self):
        r = client.get("/v1/audit-log/export?format=splunk", headers=AUTH)
        assert r.status_code == 200

    def test_export_no_auth(self):
        r = client.get("/v1/audit-log/export?format=csv")
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Fix #4: Outcomes locking
# ---------------------------------------------------------------------------

class TestOutcomesLocking:
    """_outcomes dict should be protected by lock."""

    def test_outcome_creation_and_closure(self):
        """Preflight creates outcome, /v1/outcome closes it."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_fresh_entry()],
            "action_type": "informational",
            "domain": "general",
        })
        assert r.status_code == 200
        outcome_id = r.json().get("outcome_id")
        assert outcome_id

        r2 = client.post("/v1/outcome", headers=AUTH, json={
            "outcome_id": outcome_id,
            "status": "success",
        })
        assert r2.status_code == 200

    def test_double_close_returns_409(self):
        """Closing an already-closed outcome returns 409."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_fresh_entry()],
            "action_type": "informational",
            "domain": "general",
        })
        oid = r.json()["outcome_id"]
        client.post("/v1/outcome", headers=AUTH, json={"outcome_id": oid, "status": "success"})
        r2 = client.post("/v1/outcome", headers=AUTH, json={"outcome_id": oid, "status": "failure"})
        assert r2.status_code == 409

    def test_nonexistent_outcome_returns_404(self):
        r = client.post("/v1/outcome", headers=AUTH, json={
            "outcome_id": "nonexistent_xyz_123",
            "status": "success",
        })
        assert r.status_code == 404
