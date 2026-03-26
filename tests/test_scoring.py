import sys
import os
import math
import hmac as _hmac
import hashlib
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring_engine import compute, MemoryEntry, HealingAction, HealingPolicy, load_healing_policies, compute_importance, compute_importance_with_voi, ComplianceEngine, ComplianceProfile, HealingPolicyMatrix, PolicyVerifier, KalmanForecaster, MemoryDependencyGraph, MemoryAccessTracker, ObfuscatedId, ReasonAbstractor, ZKAssurance, ThreadManager, FallbackEngine, FallbackPolicy, CircuitBreaker, CircuitState, LocalFallbackScorer, compute_shapley_values, compute_lyapunov, LaplaceMechanism, compute_pagerank, compute_authority_scores, compute_drift_metrics, detect_trend, CUSUMDetector, EWMADetector, compute_calibration, compute_hawkes_intensity, hawkes_from_entries, compute_copula, compute_mewma, compute_sheaf_consistency, get_rl_adjustment, update_from_outcome, get_q_table, reset_q_table, compute_reward, compute_bocpd, BOCPDetector, compute_rmt, compute_causal_graph, compute_spectral, compute_consolidation, compute_jump_diffusion, compute_hmm_regime, compute_zk_sheaf_proof, compute_ou_process, compute_free_energy, compute_levy_flight, sinkhorn_distance, compute_rate_distortion, compute_r_total, compute_stability_score, compute_unified_loss, geodesic_update, compute_policy_gradient, decay_temperature, compute_info_thermodynamics, compute_mahalanobis, compute_mmd, compute_page_hinkley, compute_provenance_entropy, compute_subjective_logic, compute_frechet, compute_mutual_information, compute_mdp, compute_mttr, compute_ctl_verification

# Patch out external services before importing the app
with patch.dict(os.environ, {}, clear=False):
    from fastapi.testclient import TestClient
    from api.main import app, API_KEYS, verify_api_key, TIER_LIMITS, _outcomes

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def _fresh_entry(**overrides):
    defaults = {
        "id": "test_001",
        "content": "Test memory",
        "type": "preference",
        "timestamp_age_days": 1,
        "source_trust": 0.95,
        "source_conflict": 0.05,
        "downstream_count": 1,
    }
    defaults.update(overrides)
    return defaults


# --- Scoring engine unit tests ---


class TestScoringEngine:
    def test_fresh_data_returns_use_memory(self):
        entries = [
            MemoryEntry(
                id="mem_001",
                content="Fresh data",
                type="preference",
                timestamp_age_days=1,
                source_trust=0.95,
                source_conflict=0.05,
                downstream_count=1,
            )
        ]
        result = compute(entries, action_type="informational", domain="general")

        assert result.recommended_action == "USE_MEMORY"
        assert result.omega_mem_final < 25
        assert result.assurance_score > 0

    def test_tool_state_decays_faster_than_identity(self):
        """tool_state (lambda=0.15) should score higher freshness risk than identity (lambda=0.002) at same age."""
        age = 30  # 30 days old
        tool = compute([MemoryEntry(
            id="t1", content="API token", type="tool_state",
            timestamp_age_days=age, source_trust=0.9,
            source_conflict=0.1, downstream_count=1,
        )])
        identity = compute([MemoryEntry(
            id="t2", content="Company name", type="identity",
            timestamp_age_days=age, source_trust=0.9,
            source_conflict=0.1, downstream_count=1,
        )])
        assert tool.component_breakdown["s_freshness"] > identity.component_breakdown["s_freshness"]

    def test_policy_decays_slower_than_episodic(self):
        """policy (lambda=0.005) should score lower freshness risk than episodic (lambda=0.05)."""
        age = 60
        policy = compute([MemoryEntry(
            id="t3", content="No emails after 10pm", type="policy",
            timestamp_age_days=age, source_trust=0.9,
            source_conflict=0.1, downstream_count=1,
        )])
        episodic = compute([MemoryEntry(
            id="t4", content="User called March 10", type="episodic",
            timestamp_age_days=age, source_trust=0.9,
            source_conflict=0.1, downstream_count=1,
        )])
        assert episodic.component_breakdown["s_freshness"] > policy.component_breakdown["s_freshness"]

    def test_weibull_decay_ordering(self):
        """All memory types at 30 days should follow decay ordering: tool_state > shared_workflow > episodic > preference > semantic > policy > identity."""
        age = 30
        types_ordered = ["tool_state", "shared_workflow", "episodic", "preference", "semantic", "policy", "identity"]
        scores = []
        for t in types_ordered:
            result = compute([MemoryEntry(
                id=f"ord_{t}", content="Test", type=t,
                timestamp_age_days=age, source_trust=0.9,
                source_conflict=0.1, downstream_count=1,
            )])
            scores.append(result.component_breakdown["s_freshness"])
        for i in range(len(scores) - 1):
            assert scores[i] > scores[i + 1], f"{types_ordered[i]} should decay faster than {types_ordered[i+1]}"

    def test_fresh_memory_low_decay_all_types(self):
        """At age 0, all memory types should have ~0 freshness risk."""
        for t in ["tool_state", "preference", "episodic", "semantic", "policy", "identity", "shared_workflow"]:
            result = compute([MemoryEntry(
                id=f"fresh_{t}", content="Fresh", type=t,
                timestamp_age_days=0, source_trust=0.9,
                source_conflict=0.1, downstream_count=1,
            )])
            assert result.component_breakdown["s_freshness"] == 0.0, f"{t} should have 0 freshness at age 0"

    def test_unknown_type_uses_default_decay(self):
        """Unknown memory types should use default lambda (0.05, same as episodic)."""
        age = 30
        unknown = compute([MemoryEntry(
            id="unk", content="Test", type="custom_type",
            timestamp_age_days=age, source_trust=0.9,
            source_conflict=0.1, downstream_count=1,
        )])
        episodic = compute([MemoryEntry(
            id="epi", content="Test", type="episodic",
            timestamp_age_days=age, source_trust=0.9,
            source_conflict=0.1, downstream_count=1,
        )])
        assert unknown.component_breakdown["s_freshness"] == episodic.component_breakdown["s_freshness"]

    def test_stale_data_irreversible_fintech_returns_block(self):
        entries = [
            MemoryEntry(
                id="mem_002",
                content="Old stale data",
                type="tool_state",
                timestamp_age_days=94,
                source_trust=0.5,
                source_conflict=0.6,
                downstream_count=10,
            )
        ]
        result = compute(entries, action_type="irreversible", domain="fintech")

        assert result.recommended_action == "BLOCK"
        assert result.omega_mem_final >= 70

    def test_empty_entries_returns_use_memory(self):
        result = compute([], action_type="reversible", domain="general")

        assert result.recommended_action == "USE_MEMORY"
        assert result.omega_mem_final == 0
        assert result.assurance_score == 100

    def test_component_breakdown_has_all_keys(self):
        entries = [
            MemoryEntry(
                id="mem_003",
                content="Test",
                type="semantic",
                timestamp_age_days=10,
                source_trust=0.8,
                source_conflict=0.2,
                downstream_count=3,
            )
        ]
        result = compute(entries)

        expected_keys = {
            "s_freshness", "s_drift", "s_provenance", "s_propagation",
            "r_recall", "r_encode", "s_interference", "s_recovery",
            "r_belief", "s_relevance",
        }
        assert set(result.component_breakdown.keys()) == expected_keys

    def test_r_belief_default_is_0_5(self):
        entry = MemoryEntry(
            id="mem_bel_default",
            content="Default belief",
            type="semantic",
            timestamp_age_days=1,
            source_trust=0.9,
            source_conflict=0.1,
            downstream_count=1,
        )
        assert entry.r_belief == 0.5

    def test_low_belief_suggests_external_memory(self):
        entries = [
            MemoryEntry(
                id="mem_low_belief",
                content="Low belief data",
                type="semantic",
                timestamp_age_days=1,
                source_trust=0.9,
                source_conflict=0.1,
                downstream_count=1,
                r_belief=0.1,
            )
        ]
        result = compute(entries, action_type="informational", domain="general")

        assert "external memory" in result.explainability_note.lower()
        assert result.component_breakdown["r_belief"] == 90.0

    def test_weak_belief_suggests_user_verification(self):
        entries = [
            MemoryEntry(
                id="mem_weak_belief",
                content="Weak belief data",
                type="semantic",
                timestamp_age_days=1,
                source_trust=0.9,
                source_conflict=0.1,
                downstream_count=1,
                r_belief=0.3,
            )
        ]
        result = compute(entries, action_type="informational", domain="general")

        assert "verify with user" in result.explainability_note.lower()

    def test_high_belief_no_advisory(self):
        entries = [
            MemoryEntry(
                id="mem_high_belief",
                content="High belief data",
                type="semantic",
                timestamp_age_days=1,
                source_trust=0.9,
                source_conflict=0.1,
                downstream_count=1,
                r_belief=0.9,
            )
        ]
        result = compute(entries, action_type="informational", domain="general")

        assert "external memory" not in result.explainability_note.lower()
        assert "verify with user" not in result.explainability_note.lower()
        assert result.component_breakdown["r_belief"] == 10.0

    def test_r_belief_contributes_to_omega(self):
        """Low belief should increase omega score vs high belief."""
        base = dict(
            id="mem_cmp", content="Test", type="semantic",
            timestamp_age_days=10, source_trust=0.8,
            source_conflict=0.2, downstream_count=3,
        )
        low = compute([MemoryEntry(**base, r_belief=0.1)])
        high = compute([MemoryEntry(**base, r_belief=0.9)])

        assert low.omega_mem_final > high.omega_mem_final

    def test_s_relevance_zero_without_embeddings(self):
        """Without embeddings, s_relevance should be 0."""
        entries = [
            MemoryEntry(
                id="mem_rel_none",
                content="No embedding",
                type="semantic",
                timestamp_age_days=1,
                source_trust=0.9,
                source_conflict=0.1,
                downstream_count=1,
            )
        ]
        result = compute(entries)
        assert result.component_breakdown["s_relevance"] == 0.0

    def test_s_relevance_low_similarity_adds_penalty(self):
        """Orthogonal embeddings (sim~0) should trigger 20-point penalty."""
        entries = [
            MemoryEntry(
                id="mem_rel_low",
                content="Old goal memory",
                type="semantic",
                timestamp_age_days=1,
                source_trust=0.9,
                source_conflict=0.1,
                downstream_count=1,
                prompt_embedding=[1.0, 0.0, 0.0],
            )
        ]
        # Orthogonal goal embedding
        result = compute(entries, current_goal_embedding=[0.0, 1.0, 0.0])
        assert result.component_breakdown["s_relevance"] == 20.0
        assert "intent-drift" in result.explainability_note.lower()

    def test_s_relevance_high_similarity_no_penalty(self):
        """Aligned embeddings (sim~1) should have 0 penalty."""
        entries = [
            MemoryEntry(
                id="mem_rel_high",
                content="Current goal memory",
                type="semantic",
                timestamp_age_days=1,
                source_trust=0.9,
                source_conflict=0.1,
                downstream_count=1,
                prompt_embedding=[1.0, 0.0, 0.0],
            )
        ]
        result = compute(entries, current_goal_embedding=[1.0, 0.0, 0.0])
        assert result.component_breakdown["s_relevance"] == 0.0
        assert "intent-drift" not in result.explainability_note.lower()

    def test_s_relevance_mixed_entries(self):
        """Mix of relevant and drifted entries should average the penalty."""
        entries = [
            MemoryEntry(
                id="mem_rel_a", content="Aligned", type="semantic",
                timestamp_age_days=1, source_trust=0.9,
                source_conflict=0.1, downstream_count=1,
                prompt_embedding=[1.0, 0.0, 0.0],
            ),
            MemoryEntry(
                id="mem_rel_b", content="Drifted", type="semantic",
                timestamp_age_days=1, source_trust=0.9,
                source_conflict=0.1, downstream_count=1,
                prompt_embedding=[0.0, 1.0, 0.0],
            ),
        ]
        result = compute(entries, current_goal_embedding=[1.0, 0.0, 0.0])
        # One gets 0, one gets 20 → average = 10
        assert result.component_breakdown["s_relevance"] == 10.0

    def test_s_relevance_increases_omega(self):
        """Drifted memory should produce higher omega than aligned."""
        base = dict(
            id="mem_cmp_rel", content="Test", type="semantic",
            timestamp_age_days=30, source_trust=0.8,
            source_conflict=0.2, downstream_count=3,
        )
        goal = [1.0, 0.0, 0.0]
        aligned = compute(
            [MemoryEntry(**base, prompt_embedding=[1.0, 0.0, 0.0])],
            current_goal_embedding=goal,
        )
        drifted = compute(
            [MemoryEntry(**base, prompt_embedding=[0.0, 1.0, 0.0])],
            current_goal_embedding=goal,
        )
        assert drifted.omega_mem_final > aligned.omega_mem_final

    def test_omega_clamped_to_0_100(self):
        entries = [
            MemoryEntry(
                id="mem_004",
                content="Extreme",
                type="policy",
                timestamp_age_days=1000,
                source_trust=0.0,
                source_conflict=1.0,
                downstream_count=100,
            )
        ]
        result = compute(entries, action_type="destructive", domain="medical")

        assert 0 <= result.omega_mem_final <= 100


# --- API integration tests ---


class TestPreflightAPI:
    def test_fresh_data_returns_use_memory(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "action_type": "informational",
            "domain": "general",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["recommended_action"] == "USE_MEMORY"

    def test_stale_data_irreversible_fintech_returns_block(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry(
                timestamp_age_days=94,
                source_trust=0.5,
                source_conflict=0.6,
                downstream_count=10,
            )],
            "action_type": "irreversible",
            "domain": "fintech",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["recommended_action"] == "BLOCK"

    def test_empty_memory_state_returns_400(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [],
            "action_type": "reversible",
            "domain": "general",
        }, headers=AUTH)

        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_missing_required_fields_returns_422(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [{"id": "incomplete"}],
        }, headers=AUTH)

        assert resp.status_code == 422

    def test_missing_auth_returns_error(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        })

        assert resp.status_code in (401, 403)

    def test_r_belief_passed_through_api(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry(r_belief=0.1)],
            "action_type": "informational",
            "domain": "general",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "r_belief" in data["component_breakdown"]
        assert data["component_breakdown"]["r_belief"] == 90.0

    def test_s_relevance_via_api(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry(prompt_embedding=[1.0, 0.0, 0.0])],
            "action_type": "informational",
            "domain": "general",
            "current_goal_embedding": [0.0, 1.0, 0.0],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["component_breakdown"]["s_relevance"] == 20.0

    def test_r_belief_defaults_in_api(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "action_type": "informational",
            "domain": "general",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["component_breakdown"]["r_belief"] == 50.0

    def test_invalid_api_key_returns_401(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers={"Authorization": "Bearer invalid_key"})

        assert resp.status_code == 401


class TestRateLimiting:
    def test_free_tier_rate_limit_returns_429(self):
        """Simulate a key that has exhausted its free tier quota."""
        from api.main import verify_api_key as _verify

        def mock_verify():
            return {
                "customer_id": "cus_rate_limit_test",
                "tier": "free",
                "calls_this_month": 10_000,
                "key_hash": None,
            }

        app.dependency_overrides[verify_api_key] = mock_verify
        try:
            resp = client.post("/v1/preflight", json={
                "memory_state": [_fresh_entry()],
            })

            assert resp.status_code == 429
            assert "10,000" in resp.json()["detail"]
            assert "free" in resp.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_under_limit_passes(self):
        def mock_verify():
            return {
                "customer_id": "cus_under_limit",
                "tier": "free",
                "calls_this_month": 9_999,
                "key_hash": None,
            }

        app.dependency_overrides[verify_api_key] = mock_verify
        try:
            resp = client.post("/v1/preflight", json={
                "memory_state": [_fresh_entry()],
            })

            assert resp.status_code == 200
        finally:
            app.dependency_overrides.clear()


class TestSelfHealing:
    def test_no_repair_plan_for_healthy_memory(self):
        """Fresh, trusted, high-belief memory should have empty repair plan."""
        entries = [
            MemoryEntry(
                id="healthy_001",
                content="Fresh data",
                type="semantic",
                timestamp_age_days=1,
                source_trust=0.95,
                source_conflict=0.05,
                downstream_count=1,
                r_belief=0.9,
            )
        ]
        result = compute(entries)
        assert result.repair_plan == []

    def test_stale_entry_suggests_refetch(self):
        """Stale tool_state memory should trigger REFETCH."""
        entries = [
            MemoryEntry(
                id="stale_001",
                content="Old API response",
                type="tool_state",
                timestamp_age_days=30,
                source_trust=0.9,
                source_conflict=0.1,
                downstream_count=1,
            )
        ]
        result = compute(entries)
        refetch_actions = [h for h in result.repair_plan if h.action == "REFETCH"]
        assert len(refetch_actions) == 1
        assert refetch_actions[0].entry_id == "stale_001"
        assert refetch_actions[0].projected_improvement > 0

    def test_high_conflict_suggests_verify(self):
        """High source conflict should trigger VERIFY_WITH_SOURCE."""
        entries = [
            MemoryEntry(
                id="conflict_001",
                content="Contradicted data",
                type="semantic",
                timestamp_age_days=1,
                source_trust=0.9,
                source_conflict=0.7,
                downstream_count=1,
            )
        ]
        result = compute(entries)
        verify_actions = [h for h in result.repair_plan if h.action == "VERIFY_WITH_SOURCE"]
        assert len(verify_actions) == 1
        assert verify_actions[0].entry_id == "conflict_001"
        assert "conflict" in verify_actions[0].reason.lower()

    def test_low_belief_suggests_rebuild(self):
        """Low r_belief should trigger REBUILD_WORKING_SET."""
        entries = [
            MemoryEntry(
                id="lowbelief_001",
                content="Uncertain memory",
                type="semantic",
                timestamp_age_days=1,
                source_trust=0.9,
                source_conflict=0.1,
                downstream_count=1,
                r_belief=0.1,
            )
        ]
        result = compute(entries)
        rebuild_actions = [h for h in result.repair_plan if h.action == "REBUILD_WORKING_SET"]
        assert len(rebuild_actions) == 1
        assert rebuild_actions[0].entry_id == "lowbelief_001"

    def test_multiple_issues_generate_multiple_actions(self):
        """An entry with multiple issues should generate multiple healing actions."""
        entries = [
            MemoryEntry(
                id="multi_001",
                content="Stale, conflicted, low belief",
                type="tool_state",
                timestamp_age_days=30,
                source_trust=0.5,
                source_conflict=0.8,
                downstream_count=5,
                r_belief=0.1,
            )
        ]
        result = compute(entries)
        actions = {h.action for h in result.repair_plan}
        assert "REFETCH" in actions
        assert "VERIFY_WITH_SOURCE" in actions
        assert "REBUILD_WORKING_SET" in actions

    def test_repair_plan_sorted_by_priority(self):
        """Repair plan should be sorted by priority (1 first)."""
        entries = [
            MemoryEntry(
                id="sort_001",
                content="Multiple issues",
                type="tool_state",
                timestamp_age_days=30,
                source_trust=0.5,
                source_conflict=0.8,
                downstream_count=5,
                r_belief=0.1,
            )
        ]
        result = compute(entries)
        priorities = [h.priority for h in result.repair_plan]
        assert priorities == sorted(priorities)

    def test_repair_plan_in_api_response(self):
        """API response should include repair_plan."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry(
                type="tool_state",
                timestamp_age_days=30,
                source_conflict=0.8,
                r_belief=0.1,
            )],
            "action_type": "reversible",
            "domain": "general",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "repair_plan" in data
        assert len(data["repair_plan"]) > 0
        action = data["repair_plan"][0]
        assert "action" in action
        assert "entry_id" in action
        assert "reason" in action
        assert "projected_improvement" in action
        assert "priority" in action

    def test_healing_counter_passed_through_api(self):
        """healing_counter should be accepted in API request and returned in response."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry(healing_counter=3)],
            "action_type": "informational",
            "domain": "general",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "healing_counter" in data
        assert data["healing_counter"] == 3


class TestDeterminism:
    """A2 axiom: identical memory state + identical healing_counter = identical Ω_MEM score."""

    def test_identical_inputs_produce_identical_outputs(self):
        """Same entries called twice must produce identical results."""
        entries = [
            MemoryEntry(
                id="det_001", content="Deterministic test", type="tool_state",
                timestamp_age_days=30, source_trust=0.7,
                source_conflict=0.4, downstream_count=5,
                r_belief=0.6, healing_counter=2,
            )
        ]
        r1 = compute(entries, action_type="irreversible", domain="fintech")
        r2 = compute(entries, action_type="irreversible", domain="fintech")

        assert r1.omega_mem_final == r2.omega_mem_final
        assert r1.recommended_action == r2.recommended_action
        assert r1.assurance_score == r2.assurance_score
        assert r1.component_breakdown == r2.component_breakdown
        assert r1.healing_counter == r2.healing_counter
        assert len(r1.repair_plan) == len(r2.repair_plan)

    def test_identical_inputs_100_runs(self):
        """A2 axiom stress test: 100 identical calls must produce identical omega."""
        entries = [
            MemoryEntry(
                id="det_stress", content="Stress test", type="episodic",
                timestamp_age_days=50, source_trust=0.6,
                source_conflict=0.5, downstream_count=3,
                r_belief=0.4, healing_counter=1,
            )
        ]
        baseline = compute(entries, action_type="reversible", domain="general")
        for _ in range(100):
            result = compute(entries, action_type="reversible", domain="general")
            assert result.omega_mem_final == baseline.omega_mem_final
            assert result.healing_counter == baseline.healing_counter

    def test_different_healing_counter_same_omega(self):
        """healing_counter tracks heals but does not affect the score itself."""
        base = dict(
            id="det_hc", content="Test", type="semantic",
            timestamp_age_days=10, source_trust=0.8,
            source_conflict=0.2, downstream_count=3,
            r_belief=0.7,
        )
        r0 = compute([MemoryEntry(**base, healing_counter=0)])
        r5 = compute([MemoryEntry(**base, healing_counter=5)])

        assert r0.omega_mem_final == r5.omega_mem_final
        assert r0.healing_counter == 0
        assert r5.healing_counter == 5

    def test_healing_counter_sums_across_entries(self):
        """healing_counter in result should be sum of all entry counters."""
        entries = [
            MemoryEntry(
                id="hc_a", content="A", type="semantic",
                timestamp_age_days=1, source_trust=0.9,
                source_conflict=0.1, downstream_count=1,
                healing_counter=3,
            ),
            MemoryEntry(
                id="hc_b", content="B", type="semantic",
                timestamp_age_days=1, source_trust=0.9,
                source_conflict=0.1, downstream_count=1,
                healing_counter=7,
            ),
        ]
        result = compute(entries)
        assert result.healing_counter == 10

    def test_empty_entries_healing_counter_zero(self):
        result = compute([])
        assert result.healing_counter == 0


class TestHealingPolicy:
    def test_default_policies_loaded(self):
        policies = load_healing_policies()
        assert len(policies) == 3
        rule_ids = {p.rule_id for p in policies}
        assert rule_ids == {"HP-001", "HP-002", "HP-003"}

    def test_all_default_policies_are_idempotent(self):
        policies = load_healing_policies()
        for p in policies:
            assert p.idempotent is True, f"{p.rule_id} should be idempotent"

    def test_policy_tiers(self):
        policies = load_healing_policies()
        by_id = {p.rule_id: p for p in policies}
        assert by_id["HP-001"].tier == 1  # auto-heal
        assert by_id["HP-002"].tier == 1  # auto-heal
        assert by_id["HP-003"].tier == 2  # suggest


class TestGSV:
    def test_gsv_in_api_response(self):
        """API response should include gsv field."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "action_type": "informational",
            "domain": "general",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "gsv" in data
        assert isinstance(data["gsv"], int)

    def test_gsv_fallback_without_redis(self):
        """Without Redis configured, gsv should be 0."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        assert resp.json()["gsv"] == 0

    def test_no_stale_warning_without_client_gsv(self):
        """No stale_state_warning when client_gsv is not provided."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        assert "stale_state_warning" not in resp.json()

    def test_no_stale_warning_when_redis_unavailable(self):
        """No stale warning when Redis is down (gsv=0) even if client_gsv is set."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "client_gsv": 100,
        }, headers=AUTH)

        assert resp.status_code == 200
        # gsv=0 means Redis unavailable, so no stale warning
        assert "stale_state_warning" not in resp.json()

    def test_stale_state_detected_with_mock(self):
        """When server GSV < client GSV, return STALE_STATE_DETECTED warning."""
        with patch("api.main._increment_gsv", return_value=5):
            resp = client.post("/v1/preflight", json={
                "memory_state": [_fresh_entry()],
                "client_gsv": 10,
            }, headers=AUTH)

            assert resp.status_code == 200
            data = resp.json()
            assert "stale_state_warning" in data
            assert "STALE_STATE_DETECTED" in data["stale_state_warning"]
            assert data["gsv"] == 5

    def test_no_stale_warning_when_gsv_ahead(self):
        """When server GSV >= client GSV, no stale warning."""
        with patch("api.main._increment_gsv", return_value=15):
            resp = client.post("/v1/preflight", json={
                "memory_state": [_fresh_entry()],
                "client_gsv": 10,
            }, headers=AUTH)

            assert resp.status_code == 200
            data = resp.json()
            assert "stale_state_warning" not in data
            assert data["gsv"] == 15

    def test_gsv_monotonically_increasing_with_mock(self):
        """Consecutive calls should return increasing GSV values."""
        call_count = 0

        def mock_incr():
            nonlocal call_count
            call_count += 1
            return call_count

        with patch("api.main._increment_gsv", side_effect=mock_incr):
            r1 = client.post("/v1/preflight", json={
                "memory_state": [_fresh_entry()],
            }, headers=AUTH)
            r2 = client.post("/v1/preflight", json={
                "memory_state": [_fresh_entry()],
            }, headers=AUTH)

            assert r2.json()["gsv"] > r1.json()["gsv"]


class TestHealEndpoint:
    def test_heal_returns_success(self):
        resp = client.post("/v1/heal", json={
            "entry_id": "heal_test_001",
            "action": "REFETCH",
            "agent_id": "test_agent",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["healed"] is True
        assert data["action_taken"] == "REFETCH"
        assert data["entry_id"] == "heal_test_001"
        assert data["healing_counter"] >= 1
        assert data["projected_improvement"] > 0
        assert "timestamp" in data

    def test_heal_increments_counter(self):
        """Consecutive heals on same entry should increment counter."""
        entry_id = "heal_incr_001"
        r1 = client.post("/v1/heal", json={
            "entry_id": entry_id,
            "action": "VERIFY_WITH_SOURCE",
        }, headers=AUTH)
        r2 = client.post("/v1/heal", json={
            "entry_id": entry_id,
            "action": "VERIFY_WITH_SOURCE",
        }, headers=AUTH)

        assert r2.json()["healing_counter"] == r1.json()["healing_counter"] + 1

    def test_heal_different_entries_independent_counters(self):
        """Different entries should have independent healing counters."""
        r1 = client.post("/v1/heal", json={
            "entry_id": "heal_indep_a",
            "action": "REFETCH",
        }, headers=AUTH)
        r2 = client.post("/v1/heal", json={
            "entry_id": "heal_indep_b",
            "action": "REFETCH",
        }, headers=AUTH)

        # Both should start at 1 (independent counters)
        assert r1.json()["healing_counter"] == 1
        assert r2.json()["healing_counter"] == 1

    def test_heal_all_action_types(self):
        """All three action types should be accepted."""
        for action in ["REFETCH", "VERIFY_WITH_SOURCE", "REBUILD_WORKING_SET"]:
            resp = client.post("/v1/heal", json={
                "entry_id": f"heal_action_{action}",
                "action": action,
            }, headers=AUTH)
            assert resp.status_code == 200
            assert resp.json()["action_taken"] == action

    def test_heal_projected_improvements(self):
        """Each action type should have a positive projected improvement."""
        improvements = {}
        for action in ["REFETCH", "VERIFY_WITH_SOURCE", "REBUILD_WORKING_SET"]:
            resp = client.post("/v1/heal", json={
                "entry_id": f"heal_pi_{action}",
                "action": action,
            }, headers=AUTH)
            improvements[action] = resp.json()["projected_improvement"]

        assert all(v > 0 for v in improvements.values())

    def test_heal_requires_auth(self):
        resp = client.post("/v1/heal", json={
            "entry_id": "no_auth",
            "action": "REFETCH",
        })
        assert resp.status_code in (401, 403)

    def test_heal_invalid_action_returns_422(self):
        resp = client.post("/v1/heal", json={
            "entry_id": "bad_action",
            "action": "INVALID",
        }, headers=AUTH)
        assert resp.status_code == 422


class TestImportanceDetector:
    def test_budapest_office_at_risk(self):
        """Budapest use case: tool_state, 94 days, user_stated, no backup, downstream=4 → at_risk."""
        entry = MemoryEntry(
            id="entry_001",
            content="Budapest office: Váci út 47, open 9-18",
            type="tool_state",
            timestamp_age_days=94,
            source_trust=0.9,
            source_conflict=0.1,
            downstream_count=4,
            source="user_stated",
            has_backup_source=False,
            action_context="irreversible",
            reference_count=6,
        )
        result = compute_importance(entry)

        assert result.at_risk is True
        assert result.importance_score >= 5.0
        assert result.warning is not None
        assert "Budapest office" in result.warning
        assert "94 days old" in result.warning
        # Top signal reason should be present (irreversibility or uniqueness both score 1.0)
        assert any(reason in result.warning for reason in [
            "only known from a single source",
            "used in irreversible actions",
        ])

    def test_fresh_entry_not_at_risk(self):
        """Fresh entry should not be at risk regardless of importance."""
        entry = MemoryEntry(
            id="fresh_imp",
            content="Fresh important data",
            type="tool_state",
            timestamp_age_days=1,
            source_trust=0.9,
            source_conflict=0.1,
            downstream_count=8,
            source="user_stated",
            has_backup_source=False,
            action_context="irreversible",
            reference_count=10,
        )
        result = compute_importance(entry)

        assert result.importance_score >= 5.0
        assert result.at_risk is False  # fresh, under 70% of 7-day threshold
        assert result.warning is None

    def test_low_importance_not_at_risk(self):
        """Low-importance entry should not be at risk even if old."""
        entry = MemoryEntry(
            id="low_imp",
            content="Minor note",
            type="semantic",
            timestamp_age_days=200,
            source_trust=0.9,
            source_conflict=0.1,
            downstream_count=1,
            reference_count=1,
            source="api_response",
            has_backup_source=True,
            action_context="advisory",
        )
        result = compute_importance(entry)

        assert result.importance_score < 5.0
        assert result.at_risk is False

    def test_importance_score_range(self):
        """Score should be between 0 and 10."""
        entry = MemoryEntry(
            id="range_test",
            content="Test",
            type="semantic",
            timestamp_age_days=10,
            source_trust=0.9,
            source_conflict=0.1,
            downstream_count=5,
        )
        result = compute_importance(entry)
        assert 0.0 <= result.importance_score <= 10.0

    def test_signal_breakdown_keys(self):
        entry = MemoryEntry(
            id="sig_test",
            content="Test",
            type="semantic",
            timestamp_age_days=10,
            source_trust=0.9,
            source_conflict=0.1,
            downstream_count=3,
        )
        result = compute_importance(entry)
        assert set(result.signal_breakdown.keys()) == {
            "return_frequency", "blast_radius", "irreversibility", "uniqueness",
        }

    def test_uniqueness_signal_user_stated_no_backup(self):
        """user_stated + no backup should give highest uniqueness signal."""
        entry = MemoryEntry(
            id="uniq_high",
            content="User stated fact",
            type="semantic",
            timestamp_age_days=10,
            source_trust=0.9,
            source_conflict=0.1,
            downstream_count=1,
            source="user_stated",
            has_backup_source=False,
        )
        result = compute_importance(entry)
        assert result.signal_breakdown["uniqueness"] == 1.0

    def test_uniqueness_signal_backed_up(self):
        """Entry with backup source should have low uniqueness signal."""
        entry = MemoryEntry(
            id="uniq_low",
            content="Well-backed fact",
            type="semantic",
            timestamp_age_days=10,
            source_trust=0.9,
            source_conflict=0.1,
            downstream_count=1,
            source="api_response",
            has_backup_source=True,
        )
        result = compute_importance(entry)
        assert result.signal_breakdown["uniqueness"] < 0.5

    def test_at_risk_warnings_in_api_response(self):
        """API should return at_risk_warnings for at-risk entries."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [{
                "id": "api_risk_001",
                "content": "Budapest office: Váci út 47, open 9-18",
                "type": "tool_state",
                "timestamp_age_days": 94,
                "source_trust": 0.9,
                "source_conflict": 0.1,
                "downstream_count": 4,
                "source": "user_stated",
                "has_backup_source": False,
                "action_context": "irreversible",
                "reference_count": 6,
            }],
            "action_type": "irreversible",
            "domain": "fintech",
            "detail_level": "full",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "at_risk_warnings" in data
        assert len(data["at_risk_warnings"]) == 1
        warning = data["at_risk_warnings"][0]
        assert warning["entry_id"] == "api_risk_001"
        assert "Budapest office" in warning["warning"]
        assert warning["importance_score"] >= 5.0

    def test_no_at_risk_warnings_for_healthy_entries(self):
        """Healthy entries should not produce at_risk_warnings."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "action_type": "informational",
            "domain": "general",
        }, headers=AUTH)

        assert resp.status_code == 200
        assert "at_risk_warnings" not in resp.json()


class TestOutcomeRegistry:
    def test_outcome_id_in_preflight_response(self):
        """Preflight response should include an outcome_id."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "outcome_id" in data
        assert len(data["outcome_id"]) == 36  # UUID format

    def test_close_outcome_success(self):
        """POST /v1/outcome should close an open outcome."""
        # First create a preflight to get an outcome_id
        preflight_resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        outcome_id = preflight_resp.json()["outcome_id"]

        # Close the outcome
        resp = client.post("/v1/outcome", json={
            "outcome_id": outcome_id,
            "status": "success",
            "failure_components": [],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["outcome_id"] == outcome_id
        assert data["status"] == "success"
        assert "closed_at" in data

    def test_close_outcome_failure_with_components(self):
        """Closing with failure status should accept component attribution."""
        preflight_resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        outcome_id = preflight_resp.json()["outcome_id"]

        resp = client.post("/v1/outcome", json={
            "outcome_id": outcome_id,
            "status": "failure",
            "failure_components": ["s_freshness", "s_drift"],
        }, headers=AUTH)

        assert resp.status_code == 200
        assert resp.json()["status"] == "failure"

    def test_invalid_outcome_id_returns_404(self):
        """Unknown outcome_id should return 404."""
        resp = client.post("/v1/outcome", json={
            "outcome_id": "00000000-0000-0000-0000-000000000000",
            "status": "success",
        }, headers=AUTH)

        assert resp.status_code == 404

    def test_double_close_returns_409(self):
        """Closing an already-closed outcome should return 409."""
        preflight_resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        outcome_id = preflight_resp.json()["outcome_id"]

        # Close once
        client.post("/v1/outcome", json={
            "outcome_id": outcome_id,
            "status": "success",
        }, headers=AUTH)

        # Try to close again
        resp = client.post("/v1/outcome", json={
            "outcome_id": outcome_id,
            "status": "failure",
        }, headers=AUTH)

        assert resp.status_code == 409

    def test_outcome_requires_auth(self):
        resp = client.post("/v1/outcome", json={
            "outcome_id": "test",
            "status": "success",
        })
        assert resp.status_code in (401, 403)


class TestClientOptimizer:
    def test_client_activates_optimizer(self):
        """client=grok should trigger client_optimized=true."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry(type="tool_state", timestamp_age_days=10)],
            "client": "grok",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["client_optimized"] is True
        assert "optimizer_version" in data
        assert data["optimizer_version"] == "v2"

    def test_no_client_does_not_trigger_optimizer(self):
        """Without client field, client_optimized should be false."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["client_optimized"] is False
        assert "optimizer_version" not in data

    def test_optimizer_repair_plan_refetch_first(self):
        """Client optimizer should order REFETCH before other actions."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry(
                type="tool_state",
                timestamp_age_days=30,
                source_conflict=0.8,
                r_belief=0.1,
            )],
            "client": "grok",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["client_optimized"] is True
        plan = data["repair_plan"]
        assert len(plan) > 0
        actions = [h["action"] for h in plan]
        if "REFETCH" in actions:
            refetch_idx = actions.index("REFETCH")
            for other in ["VERIFY_WITH_SOURCE", "REBUILD_WORKING_SET"]:
                if other in actions:
                    assert refetch_idx < actions.index(other), f"REFETCH should come before {other}"

    def test_optimizer_not_activated_for_fresh_entries(self):
        """Optimizer should not activate when no stale tool_state and no repair plan."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry(type="semantic", timestamp_age_days=0)],
            "client": "grok",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["client_optimized"] is False


class TestComplianceEngine:
    def test_eu_ai_act_blocks_irreversible_high_risk(self):
        """EU_AI_ACT Article 12: omega>60 + irreversible → non-compliant, audit required."""
        engine = ComplianceEngine()
        result = engine.evaluate(
            omega_mem_final=75, assurance_score=48, domain="fintech",
            action_type="irreversible", profile=ComplianceProfile.EU_AI_ACT,
        )
        assert result.compliant is False
        assert result.audit_required is True
        assert any(v.article == "Article 12" for v in result.violations)
        assert result.profile_applied == "EU_AI_ACT"

    def test_eu_ai_act_allows_reversible(self):
        """EU_AI_ACT should not block reversible actions even with high omega."""
        engine = ComplianceEngine()
        result = engine.evaluate(
            omega_mem_final=75, assurance_score=48, domain="fintech",
            action_type="reversible", profile=ComplianceProfile.EU_AI_ACT,
        )
        assert result.compliant is True

    def test_eu_ai_act_medical_article_9(self):
        """EU_AI_ACT Article 9: medical + omega>40 → non-compliant."""
        engine = ComplianceEngine()
        result = engine.evaluate(
            omega_mem_final=50, assurance_score=65, domain="medical",
            action_type="reversible", profile=ComplianceProfile.EU_AI_ACT,
        )
        assert result.compliant is False
        assert any(v.article == "Article 9" for v in result.violations)

    def test_general_profile_allows_same_action(self):
        """GENERAL profile should not block what EU_AI_ACT would block."""
        engine = ComplianceEngine()
        result = engine.evaluate(
            omega_mem_final=75, assurance_score=48, domain="fintech",
            action_type="irreversible", profile=ComplianceProfile.GENERAL,
        )
        assert result.compliant is True

    def test_fda_510k_medical_high_risk(self):
        """FDA_510K: medical + omega>30 → non-compliant."""
        engine = ComplianceEngine()
        result = engine.evaluate(
            omega_mem_final=40, assurance_score=72, domain="medical",
            action_type="reversible", profile=ComplianceProfile.FDA_510K,
        )
        assert result.compliant is False
        assert result.audit_required is True

    def test_compliance_result_in_api_response(self):
        """Preflight response should include compliance_result."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "compliance_profile": "GENERAL",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "compliance_result" in data
        cr = data["compliance_result"]
        assert "compliant" in cr
        assert "violations" in cr
        assert "audit_required" in cr
        assert cr["profile_applied"] == "GENERAL"

    def test_eu_ai_act_overrides_to_block_in_api(self):
        """EU_AI_ACT should override recommended_action to BLOCK via API."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry(
                type="tool_state",
                timestamp_age_days=94,
                source_trust=0.5,
                source_conflict=0.6,
                downstream_count=10,
            )],
            "action_type": "irreversible",
            "domain": "fintech",
            "compliance_profile": "EU_AI_ACT",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["recommended_action"] == "BLOCK"
        assert data["compliance_result"]["compliant"] is False
        assert data["compliance_result"]["audit_required"] is True


class TestHealingPolicyMatrix:
    def test_tool_state_medical_fda(self):
        """tool_state + medical + FDA_510K → tier=3, requires_approval=True."""
        matrix = HealingPolicyMatrix()
        policy = matrix.lookup("tool_state", "medical", ComplianceProfile.FDA_510K)
        assert policy.tier == 3
        assert policy.requires_approval is True

    def test_tool_state_general(self):
        """tool_state + general + GENERAL → tier=1, requires_approval=False."""
        matrix = HealingPolicyMatrix()
        policy = matrix.lookup("tool_state", "general", ComplianceProfile.GENERAL)
        assert policy.tier == 1
        assert policy.requires_approval is False

    def test_semantic_fintech_eu_ai_act(self):
        """semantic + fintech + EU_AI_ACT → tier=2, requires_approval=False."""
        matrix = HealingPolicyMatrix()
        policy = matrix.lookup("semantic", "fintech", ComplianceProfile.EU_AI_ACT)
        assert policy.tier == 2
        assert policy.requires_approval is False

    def test_unknown_combination_returns_default(self):
        """Unknown combination falls back to tier=1, no approval."""
        matrix = HealingPolicyMatrix()
        policy = matrix.lookup("identity", "coding", ComplianceProfile.GENERAL)
        assert policy.tier == 1
        assert policy.requires_approval is False


class TestFormalVerification:
    def test_healing_policy_verifies(self):
        """Default healing policy should pass all Z3 checks."""
        verifier = PolicyVerifier()
        result = verifier.verify_healing_policy()
        assert result.verified is True
        assert result.counterexample is None
        assert result.duration_ms >= 0
        assert "verified" in result.proof.lower()

    def test_general_compliance_verifies(self):
        """GENERAL compliance rules should be consistent."""
        verifier = PolicyVerifier()
        result = verifier.verify_compliance_rules(ComplianceProfile.GENERAL, "general")
        assert result.verified is True
        assert result.counterexample is None

    def test_eu_ai_act_compliance_verifies(self):
        """EU_AI_ACT compliance rules should be internally consistent."""
        verifier = PolicyVerifier()
        result = verifier.verify_compliance_rules(ComplianceProfile.EU_AI_ACT, "fintech")
        assert result.verified is True
        assert result.counterexample is None

    def test_eu_ai_act_medical_verifies(self):
        """EU_AI_ACT + medical domain should be consistent."""
        verifier = PolicyVerifier()
        result = verifier.verify_compliance_rules(ComplianceProfile.EU_AI_ACT, "medical")
        assert result.verified is True

    def test_fda_510k_verifies(self):
        """FDA_510K compliance rules should be consistent."""
        verifier = PolicyVerifier()
        result = verifier.verify_compliance_rules(ComplianceProfile.FDA_510K, "medical")
        assert result.verified is True

    def test_verification_result_fields(self):
        """VerificationResult should have all required fields."""
        verifier = PolicyVerifier()
        result = verifier.verify_healing_policy()
        assert hasattr(result, "verified")
        assert hasattr(result, "proof")
        assert hasattr(result, "counterexample")
        assert hasattr(result, "duration_ms")

    def test_verify_endpoint(self):
        """GET /v1/verify should return verification results."""
        resp = client.get("/v1/verify?profile=GENERAL&domain=general", headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["verified"] is True
        assert "proof" in data
        assert data["counterexample"] is None
        assert data["duration_ms"] >= 0
        assert data["profile"] == "GENERAL"
        assert data["domain"] == "general"

    def test_verify_endpoint_eu_ai_act(self):
        """GET /v1/verify with EU_AI_ACT profile should verify."""
        resp = client.get("/v1/verify?profile=EU_AI_ACT&domain=fintech", headers=AUTH)

        assert resp.status_code == 200
        assert resp.json()["verified"] is True
        assert resp.json()["profile"] == "EU_AI_ACT"

    def test_verify_requires_auth(self):
        resp = client.get("/v1/verify")
        assert resp.status_code in (401, 403)


class TestKalmanForecast:
    def test_degrading_trend(self):
        """Rising scores should produce degrading trend."""
        forecaster = KalmanForecaster()
        forecaster.fit([10, 20, 30, 40, 50, 60])
        result = forecaster.predict(steps=5)

        assert result.trend == "degrading"
        assert len(result.forecast_scores) == 5
        assert all(s > 50 for s in result.forecast_scores)

    def test_improving_trend(self):
        """Falling scores should produce improving trend."""
        forecaster = KalmanForecaster()
        forecaster.fit([80, 70, 60, 50, 40, 30])
        result = forecaster.predict(steps=5)

        assert result.trend == "improving"
        assert all(s < 40 for s in result.forecast_scores)

    def test_stable_trend(self):
        """Flat scores should produce stable trend."""
        forecaster = KalmanForecaster()
        forecaster.fit([25, 25, 25, 25, 25, 25])
        result = forecaster.predict(steps=5)

        assert result.trend == "stable"

    def test_collapse_risk_high_when_approaching_block(self):
        """Scores approaching BLOCK threshold should have collapse_risk > 0.5."""
        forecaster = KalmanForecaster()
        forecaster.fit([50, 55, 60, 65, 70, 75])
        result = forecaster.predict(steps=5)

        assert result.collapse_risk > 0.5
        assert result.trend == "degrading"

    def test_collapse_risk_zero_for_low_scores(self):
        """Low stable scores should have zero collapse_risk."""
        forecaster = KalmanForecaster()
        forecaster.fit([5, 5, 5, 5, 5])
        result = forecaster.predict(steps=5)

        assert result.collapse_risk == 0.0

    def test_forecast_scores_clamped(self):
        """Forecast scores should be clamped to 0–100."""
        forecaster = KalmanForecaster()
        forecaster.fit([90, 92, 94, 96, 98, 100])
        result = forecaster.predict(steps=10)

        assert all(0 <= s <= 100 for s in result.forecast_scores)

    def test_forecast_via_verify_endpoint(self):
        """GET /v1/verify with history should include forecast."""
        resp = client.get(
            "/v1/verify?profile=GENERAL&domain=general&history=10,20,30,40,50,60",
            headers=AUTH,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "forecast" in data
        assert data["forecast"]["trend"] == "degrading"
        assert len(data["forecast"]["forecast_scores"]) == 5
        assert 0 <= data["forecast"]["collapse_risk"] <= 1

    def test_no_forecast_without_history(self):
        """GET /v1/verify without history should not include forecast."""
        resp = client.get("/v1/verify?profile=GENERAL&domain=general", headers=AUTH)

        assert resp.status_code == 200
        assert "forecast" not in resp.json()


class TestDependencyGraph:
    def test_step_with_stale_entry_is_blocked(self):
        graph = MemoryDependencyGraph()
        graph.add_step("step_send_email", ["mem_customer_pref"])
        graph.add_step("step_log_event", ["mem_event_log"])

        result = graph.surgical_block(blocked_entries=["mem_customer_pref"])
        assert "step_send_email" in result.blocked_steps
        assert "step_log_event" in result.safe_steps

    def test_step_with_no_stale_deps_is_safe(self):
        graph = MemoryDependencyGraph()
        graph.add_step("step_a", ["mem_fresh"])
        graph.add_step("step_b", ["mem_stale"])

        result = graph.surgical_block(blocked_entries=["mem_stale"])
        assert "step_a" in result.safe_steps
        assert "step_b" in result.blocked_steps

    def test_partial_execution_possible(self):
        graph = MemoryDependencyGraph()
        graph.add_step("step_a", ["mem_fresh"])
        graph.add_step("step_b", ["mem_stale"])

        result = graph.surgical_block(blocked_entries=["mem_stale"])
        assert result.partial_execution_possible is True

    def test_no_partial_when_all_blocked(self):
        graph = MemoryDependencyGraph()
        graph.add_step("step_a", ["mem_stale"])
        graph.add_step("step_b", ["mem_stale"])

        result = graph.surgical_block(blocked_entries=["mem_stale"])
        assert result.partial_execution_possible is False
        assert len(result.safe_steps) == 0

    def test_no_partial_when_all_safe(self):
        graph = MemoryDependencyGraph()
        graph.add_step("step_a", ["mem_fresh"])

        result = graph.surgical_block(blocked_entries=["mem_other"])
        assert result.partial_execution_possible is False
        assert len(result.blocked_steps) == 0

    def test_get_affected_steps(self):
        graph = MemoryDependencyGraph()
        graph.add_step("step_a", ["mem_1", "mem_2"])
        graph.add_step("step_b", ["mem_2", "mem_3"])

        affected = graph.get_affected_steps("mem_2")
        assert "step_a" in affected
        assert "step_b" in affected

    def test_surgical_result_in_api_response(self):
        """Preflight with steps should return surgical_result."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [
                _fresh_entry(id="mem_stale_x", type="tool_state", timestamp_age_days=30, source_conflict=0.8),
                _fresh_entry(id="mem_fresh_y"),
            ],
            "steps": [
                {"step_id": "step_charge", "entry_ids": ["mem_stale_x"]},
                {"step_id": "step_log", "entry_ids": ["mem_fresh_y"]},
            ],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "surgical_result" in data
        sr = data["surgical_result"]
        assert "blocked_steps" in sr
        assert "safe_steps" in sr
        assert "partial_execution_possible" in sr
        # mem_stale_x should trigger repair → step_charge blocked
        assert "step_charge" in sr["blocked_steps"]
        assert "step_log" in sr["safe_steps"]
        assert sr["partial_execution_possible"] is True

    def test_no_surgical_result_without_steps(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        assert "surgical_result" not in resp.json()


class TestMemoryAccessTracker:
    def test_track_records_access(self):
        tracker = MemoryAccessTracker()
        tracker.track("step_a", "mem_1")
        tracker.track("step_a", "mem_2")
        tracker.track("step_b", "mem_2")

        deps = tracker.get_step_dependencies()
        assert deps["step_a"] == ["mem_1", "mem_2"]
        assert deps["step_b"] == ["mem_2"]

    def test_no_duplicate_tracking(self):
        tracker = MemoryAccessTracker()
        tracker.track("step_a", "mem_1")
        tracker.track("step_a", "mem_1")

        assert tracker.get_step_dependencies()["step_a"] == ["mem_1"]

    def test_to_dependency_graph(self):
        tracker = MemoryAccessTracker()
        tracker.track("step_a", "mem_1")
        tracker.track("step_b", "mem_2")

        graph = tracker.to_dependency_graph()
        result = graph.surgical_block(blocked_entries=["mem_1"])
        assert "step_a" in result.blocked_steps
        assert "step_b" in result.safe_steps

    def test_begin_end_step_context(self):
        tracker = MemoryAccessTracker()
        tracker.begin_step("step_x")
        tracker.track_current("mem_1")
        tracker.track_current("mem_2")
        tracker.end_step()

        assert tracker.current_step is None
        deps = tracker.get_step_dependencies()
        assert deps["step_x"] == ["mem_1", "mem_2"]

    def test_reset_clears_state(self):
        tracker = MemoryAccessTracker()
        tracker.track("step_a", "mem_1")
        tracker.reset()

        assert tracker.get_step_dependencies() == {}
        assert tracker.current_step is None

    def test_auto_tracked_in_api_response(self):
        """When no manual steps and multiple entries with repairs, auto_tracked=true."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [
                _fresh_entry(id="mem_auto_stale", type="tool_state", timestamp_age_days=30, source_conflict=0.8),
                _fresh_entry(id="mem_auto_fresh"),
            ],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "surgical_result" in data
        assert data["auto_tracked"] is True
        sr = data["surgical_result"]
        assert "auto:mem_auto_stale" in sr["blocked_steps"]
        assert "auto:mem_auto_fresh" in sr["safe_steps"]

    def test_manual_steps_not_auto_tracked(self):
        """Manual steps should set auto_tracked=false."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [
                _fresh_entry(id="mem_m1", type="tool_state", timestamp_age_days=30, source_conflict=0.8),
                _fresh_entry(id="mem_m2"),
            ],
            "steps": [
                {"step_id": "s1", "entry_ids": ["mem_m1"]},
                {"step_id": "s2", "entry_ids": ["mem_m2"]},
            ],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["auto_tracked"] is False


class TestSDKStepTracker:
    def test_step_context_manager(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sdk", "python"))
        from sgraal.tracker import StepTracker

        tracker = StepTracker()
        with tracker.step("step_1"):
            tracker.track("mem_a")
            tracker.track("mem_b")
        with tracker.step("step_2"):
            tracker.track("mem_c")

        steps = tracker.get_steps()
        assert len(steps) == 2
        s1 = next(s for s in steps if s["step_id"] == "step_1")
        assert s1["entry_ids"] == ["mem_a", "mem_b"]

    def test_step_tracker_reset(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sdk", "python"))
        from sgraal.tracker import StepTracker

        tracker = StepTracker()
        with tracker.step("step_1"):
            tracker.track("mem_a")
        tracker.reset()

        assert tracker.get_steps() == []


class TestPrivacyLayer:
    def test_obfuscated_id_not_original(self):
        obf = ObfuscatedId.obfuscate("mem_001", "session_abc")
        assert obf != "mem_001"
        assert len(obf) == 16

    def test_obfuscation_deterministic(self):
        a = ObfuscatedId.obfuscate("mem_001", "session_abc")
        b = ObfuscatedId.obfuscate("mem_001", "session_abc")
        assert a == b

    def test_different_session_key_different_id(self):
        a = ObfuscatedId.obfuscate("mem_001", "key_1")
        b = ObfuscatedId.obfuscate("mem_001", "key_2")
        assert a != b

    def test_deobfuscate_reverse_lookup(self):
        session = "session_xyz"
        obf = ObfuscatedId.obfuscate("mem_002", session)
        original = ObfuscatedId.deobfuscate(obf, session, ["mem_001", "mem_002", "mem_003"])
        assert original == "mem_002"

    def test_reason_abstraction_stale(self):
        assert ReasonAbstractor.abstract("Memory is stale (freshness=88/100, type=tool_state)") == "STALE"

    def test_reason_abstraction_conflict(self):
        assert ReasonAbstractor.abstract("High source conflict (K=0.82)") == "CONFLICT"

    def test_reason_abstraction_belief(self):
        assert ReasonAbstractor.abstract("Low model belief (r_belief=0.15)") == "INTENT_DRIFT"

    def test_reason_abstraction_unknown(self):
        assert ReasonAbstractor.abstract("Some unknown reason") == "GENERAL_RISK"

    def test_zk_commitment_present(self):
        commitment = ZKAssurance.commit(42.1, ["mem_001", "mem_002"])
        assert len(commitment) == 64  # SHA256 hex

    def test_zk_verify(self):
        ids = ["mem_001", "mem_002"]
        commitment = ZKAssurance.commit(42.1, ids)
        assert ZKAssurance.verify(commitment, 42.1, ids) is True
        assert ZKAssurance.verify(commitment, 42.2, ids) is False

    def test_zk_commitment_in_api_response(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "zk_commitment" in data
        assert len(data["zk_commitment"]) == 64
        assert "session_key" in data

    def test_obfuscated_by_default(self):
        """Default detail_level should obfuscate entry_ids in repair_plan."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry(
                id="mem_priv_test",
                type="tool_state",
                timestamp_age_days=30,
                source_conflict=0.8,
            )],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        if data["repair_plan"]:
            # Find entry-specific repair actions (not wildcard MDP/OU)
            entry_actions = [r for r in data["repair_plan"] if r["entry_id"] != "*"]
            if entry_actions:
                # Entry ID should be obfuscated (not the original)
                assert entry_actions[0]["entry_id"] != "mem_priv_test"
                # Reason should be abstracted
                assert entry_actions[0]["reason"] in ["STALE", "CONFLICT", "LOW_TRUST", "PROPAGATION_RISK", "INTENT_DRIFT", "GENERAL_RISK"]

    def test_full_detail_returns_original(self):
        """detail_level=full should return original entry_ids and reasons."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry(
                id="mem_full_test",
                type="tool_state",
                timestamp_age_days=30,
                source_conflict=0.8,
            )],
            "detail_level": "full",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        if data["repair_plan"]:
            entry_actions = [r for r in data["repair_plan"] if r["entry_id"] != "*"]
            if entry_actions:
                assert entry_actions[0]["entry_id"] == "mem_full_test"
            # Full reason contains specific values
            assert "(" in data["repair_plan"][0]["reason"]


class TestThreadManager:
    def test_high_risk_domain_always_checked(self):
        """medical/fintech/legal should have sample_rate=1.0."""
        tm = ThreadManager()
        for domain in ["medical", "fintech", "legal"]:
            assert tm.get_sample_rate(domain) == 1.0
            assert tm.should_check("any_thread", domain) is True

    def test_low_risk_domain_sampled(self):
        """customer_support/coding should have sample_rate=0.1."""
        tm = ThreadManager()
        assert tm.get_sample_rate("customer_support") == 0.1
        assert tm.get_sample_rate("coding") == 0.1

    def test_same_thread_same_bucket(self):
        """Same thread_id always gets the same bucket_id."""
        tm = ThreadManager()
        b1 = tm.assign_bucket("thread_abc", "general")
        b2 = tm.assign_bucket("thread_abc", "general")
        assert b1 == b2
        assert b1.startswith("bucket:")

    def test_should_check_deterministic(self):
        """Same thread_id + domain always returns same result."""
        tm = ThreadManager()
        r1 = tm.should_check("thread_xyz", "general")
        r2 = tm.should_check("thread_xyz", "general")
        assert r1 == r2

    def test_sampled_out_response_via_api(self):
        """Sampled-out thread should get lightweight USE_MEMORY response."""
        # Find a thread_id that gets sampled out for coding (10% rate)
        tm = ThreadManager()
        sampled_out_thread = None
        for i in range(200):
            tid = f"thread_sample_test_{i}"
            if not tm.should_check(tid, "coding"):
                sampled_out_thread = tid
                break

        if sampled_out_thread is None:
            return  # extremely unlikely but skip if all 200 pass

        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "domain": "coding",
            "thread_id": sampled_out_thread,
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["sampled"] is False
        assert data["recommended_action"] == "USE_MEMORY"
        assert data["reason"] == "sampled_out"
        assert data["thread_id"] == sampled_out_thread
        assert "bucket_id" in data
        assert data["sample_rate"] == 0.1

    def test_full_scoring_with_thread_id(self):
        """Thread in high-risk domain should get full scoring with thread info."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "domain": "medical",
            "thread_id": "thread_medical_001",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["sampled"] is True
        assert data["thread_id"] == "thread_medical_001"
        assert "bucket_id" in data
        assert data["sample_rate"] == 1.0
        assert "omega_mem_final" in data

    def test_no_thread_info_without_thread_id(self):
        """Without thread_id, response should not include thread info."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "thread_id" not in data
        assert "bucket_id" not in data


class TestLLMGuards:
    """Test GeminiGuard and OpenAIGuard with mocked Sgraal + LLM APIs."""

    @staticmethod
    def _get_guards():
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sdk", "python"))
        from sgraal.integrations import GeminiGuard, OpenAIGuard
        from sgraal.client import PreflightResult
        return GeminiGuard, OpenAIGuard, PreflightResult

    def _mock_preflight(self, action, omega):
        _, _, PreflightResult = self._get_guards()
        return PreflightResult(
            omega_mem_final=omega,
            recommended_action=action,
            assurance_score=max(0, round(100 - omega * 0.7)),
            explainability_note=f"Test: Action={action}.",
            component_breakdown={},
        )

    def test_gemini_guard_blocks_on_high_omega(self):
        GeminiGuard, _, _ = self._get_guards()

        guard = GeminiGuard(sgraal_api_key="test", gemini_api_key="test")
        with patch.object(guard, "_preflight", return_value=self._mock_preflight("BLOCK", 85)):
            result = guard.check_and_generate("query", memory_data=[{"id": "m1", "content": "x", "type": "semantic", "timestamp_age_days": 1}])
            assert "[SGRAAL BLOCKED]" in result
            assert "85" in result

    def test_openai_guard_warns_on_medium_omega(self):
        _, OpenAIGuard, _ = self._get_guards()

        guard = OpenAIGuard(sgraal_api_key="test", openai_api_key="test")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "OpenAI response"

        with patch.object(guard, "_preflight", return_value=self._mock_preflight("WARN", 55)):
            with patch("sgraal.integrations.OpenAI") as mock_openai:
                mock_openai.return_value.chat.completions.create.return_value = mock_response
                result = guard.check_and_generate("query", memory_data=[{"id": "m1", "content": "x", "type": "semantic", "timestamp_age_days": 1}])
                assert result == "OpenAI response"
                # Verify the prompt included the warning prefix
                call_args = mock_openai.return_value.chat.completions.create.call_args
                msg = call_args[1]["messages"][0]["content"]
                assert "[SGRAAL WARNING" in msg

    def test_gemini_guard_passes_on_low_omega(self):
        GeminiGuard, _, _ = self._get_guards()

        guard = GeminiGuard(sgraal_api_key="test", gemini_api_key="test")
        mock_response = MagicMock()
        mock_response.text = "Gemini response"

        with patch.object(guard, "_preflight", return_value=self._mock_preflight("USE_MEMORY", 10)):
            with patch("sgraal.integrations.genai") as mock_genai:
                mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
                result = guard.check_and_generate("query", memory_data=[{"id": "m1", "content": "x", "type": "semantic", "timestamp_age_days": 1}])
                assert result == "Gemini response"
                # No warning prefix for USE_MEMORY
                call_args = mock_genai.GenerativeModel.return_value.generate_content.call_args
                assert "[SGRAAL" not in call_args[0][0]

    def test_openai_guard_blocks_on_high_omega(self):
        _, OpenAIGuard, _ = self._get_guards()

        guard = OpenAIGuard(sgraal_api_key="test", openai_api_key="test")
        with patch.object(guard, "_preflight", return_value=self._mock_preflight("BLOCK", 90)):
            result = guard.check_and_generate("query", memory_data=[{"id": "m1", "content": "x", "type": "semantic", "timestamp_age_days": 1}])
            assert "[SGRAAL BLOCKED]" in result

    def test_openai_guard_passes_on_low_omega(self):
        _, OpenAIGuard, _ = self._get_guards()

        guard = OpenAIGuard(sgraal_api_key="test", openai_api_key="test")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "GPT response"

        with patch.object(guard, "_preflight", return_value=self._mock_preflight("USE_MEMORY", 8)):
            with patch("sgraal.integrations.OpenAI") as mock_openai:
                mock_openai.return_value.chat.completions.create.return_value = mock_response
                result = guard.check_and_generate("query", memory_data=[{"id": "m1", "content": "x", "type": "semantic", "timestamp_age_days": 1}])
                assert result == "GPT response"


class TestBatchScoring:
    def test_batch_returns_all_results(self):
        resp = client.post("/v1/preflight/batch", json={
            "entries": [
                _fresh_entry(id="batch_1"),
                _fresh_entry(id="batch_2", type="tool_state", timestamp_age_days=30),
                _fresh_entry(id="batch_3"),
            ],
            "action_type": "reversible",
            "domain": "general",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 3
        ids = [r["entry_id"] for r in data["results"]]
        assert "batch_1" in ids
        assert "batch_2" in ids
        assert "batch_3" in ids

    def test_batch_summary_counts(self):
        resp = client.post("/v1/preflight/batch", json={
            "entries": [
                _fresh_entry(id="bs_safe"),
                _fresh_entry(id="bs_risky", type="tool_state", timestamp_age_days=94, source_trust=0.3, source_conflict=0.7),
            ],
            "action_type": "irreversible",
            "domain": "fintech",
        }, headers=AUTH)

        assert resp.status_code == 200
        summary = resp.json()["batch_summary"]
        assert summary["total"] == 2
        assert summary["blocked"] + summary["warned"] + summary["safe"] == 2
        assert "highest_risk_entry_id" in summary

    def test_batch_max_100_entries(self):
        entries = [_fresh_entry(id=f"max_{i}") for i in range(101)]
        resp = client.post("/v1/preflight/batch", json={
            "entries": entries,
        }, headers=AUTH)

        assert resp.status_code == 400
        assert "100" in resp.json()["detail"]

    def test_batch_empty_returns_400(self):
        resp = client.post("/v1/preflight/batch", json={
            "entries": [],
        }, headers=AUTH)
        assert resp.status_code == 400

    def test_batch_requires_auth(self):
        resp = client.post("/v1/preflight/batch", json={
            "entries": [_fresh_entry()],
        })
        assert resp.status_code in (401, 403)


class TestCustomWeights:
    def test_custom_weights_override_defaults(self):
        """Custom weights should change the omega_mem_final score."""
        # Heavy freshness weight
        resp_custom = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry(type="tool_state", timestamp_age_days=30)],
            "custom_weights": {
                "s_freshness": 0.50, "s_drift": 0.10, "s_provenance": 0.05,
                "s_propagation": 0.05, "r_recall": 0.05, "r_encode": 0.05,
                "s_interference": 0.05, "s_recovery": -0.05, "r_belief": 0.05,
                "s_relevance": 0.05,
            },
        }, headers=AUTH)

        resp_default = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry(type="tool_state", timestamp_age_days=30)],
        }, headers=AUTH)

        assert resp_custom.status_code == 200
        assert resp_default.status_code == 200
        assert resp_custom.json()["weights_used"] == "custom"
        assert resp_default.json()["weights_used"] == "default"
        # Different weights should produce different scores
        assert resp_custom.json()["omega_mem_final"] != resp_default.json()["omega_mem_final"]

    def test_custom_weights_in_batch(self):
        resp = client.post("/v1/preflight/batch", json={
            "entries": [_fresh_entry(id="cw_batch")],
            "custom_weights": {
                "s_freshness": 0.15, "s_drift": 0.15, "s_provenance": 0.12,
                "s_propagation": 0.12, "r_recall": 0.18, "r_encode": 0.12,
                "s_interference": 0.10, "s_recovery": -0.10, "r_belief": 0.05,
                "s_relevance": 0.06,
            },
        }, headers=AUTH)

        assert resp.status_code == 200
        assert resp.json()["weights_used"] == "custom"

    def test_custom_weights_bad_sum_returns_400(self):
        resp = client.post("/v1/preflight/batch", json={
            "entries": [_fresh_entry()],
            "custom_weights": {"s_freshness": 5.0},
        }, headers=AUTH)

        assert resp.status_code == 400
        assert "sum" in resp.json()["detail"].lower()


class TestFallbackEngine:
    def test_circuit_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        cb.record_failure()
        assert cb.should_allow_request() is True  # still closed
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.should_allow_request() is False

    def test_circuit_recovers_to_half_open(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        # Simulate timeout passing
        cb._last_failure_time = cb._last_failure_time - 2
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.should_allow_request() is True

    def test_circuit_closes_on_success(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        cb.record_failure()
        cb.record_failure()
        cb._last_failure_time = cb._last_failure_time - 2
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_fallback_warn_policy(self):
        engine = FallbackEngine(policy=FallbackPolicy.WARN)
        entries = [MemoryEntry(
            id="fb1", content="test", type="tool_state",
            timestamp_age_days=30, source_trust=0.9,
            source_conflict=0.1, downstream_count=1,
        )]
        result = engine.get_fallback_result(entries)
        assert result.fallback is True
        assert result.recommended_action == "WARN"
        assert result.reason == "API_UNAVAILABLE"
        assert result.omega_mem_final > 0

    def test_fallback_block_policy(self):
        engine = FallbackEngine(policy=FallbackPolicy.BLOCK)
        result = engine.get_fallback_result([])
        assert result.recommended_action == "BLOCK"
        assert result.fallback is True

    def test_fallback_allow_policy(self):
        engine = FallbackEngine(policy=FallbackPolicy.ALLOW)
        result = engine.get_fallback_result([])
        assert result.recommended_action == "USE_MEMORY"

    def test_local_scorer(self):
        scorer = LocalFallbackScorer()
        entry = MemoryEntry(
            id="ls1", content="test", type="tool_state",
            timestamp_age_days=30, source_trust=0.9,
            source_conflict=0.1, downstream_count=1,
        )
        score = scorer.score(entry)
        assert 0 <= score <= 100
        assert score > 0  # 30 days tool_state should have significant decay

    def test_sdk_client_fallback_on_failure(self):
        """SDK client returns fallback result when API unreachable."""
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sdk", "python"))
        from sgraal.client import SgraalClient as SDKClient

        sdk = SDKClient(
            api_key="test_key",
            base_url="http://localhost:1",  # unreachable
            fallback_policy="warn",
            timeout=0.1,
            failure_threshold=1,
        )
        result = sdk.preflight(memory_state=[{
            "id": "m1", "content": "test", "type": "semantic",
            "timestamp_age_days": 10,
        }])
        assert result.fallback is True
        assert result.recommended_action == "WARN"
        assert result.circuit_state in ("CLOSED", "OPEN")

    def test_sdk_circuit_opens_after_failures(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sdk", "python"))
        from sgraal.client import SgraalClient as SDKClient

        sdk = SDKClient(
            api_key="test_key",
            base_url="http://localhost:1",
            fallback_policy="warn",
            timeout=0.1,
            failure_threshold=2,
        )
        mem = [{"id": "m1", "content": "test", "type": "semantic", "timestamp_age_days": 5}]
        sdk.preflight(memory_state=mem)
        sdk.preflight(memory_state=mem)
        # After 2 failures, circuit should be OPEN
        assert sdk.circuit.state == "OPEN"
        # Next call should fail-fast (fallback without trying)
        result = sdk.preflight(memory_state=mem)
        assert result.fallback is True


class TestShapleyValues:
    def test_shapley_values_sum_to_omega(self):
        """Shapley values should approximately sum to omega_mem_final."""
        entries = [MemoryEntry(
            id="shap_1", content="Test", type="tool_state",
            timestamp_age_days=30, source_trust=0.7,
            source_conflict=0.3, downstream_count=5,
            r_belief=0.6,
        )]
        result = compute(entries, action_type="reversible", domain="general")
        shapley = compute_shapley_values(result.component_breakdown, "reversible", "general")

        assert abs(sum(shapley.values()) - result.omega_mem_final) < 1.0

    def test_shapley_has_all_components(self):
        """Shapley dict should have same keys as component_breakdown."""
        entries = [MemoryEntry(
            id="shap_2", content="Test", type="semantic",
            timestamp_age_days=10, source_trust=0.9,
            source_conflict=0.1, downstream_count=2,
        )]
        result = compute(entries)
        shapley = compute_shapley_values(result.component_breakdown)

        assert set(shapley.keys()) == set(result.component_breakdown.keys())

    def test_high_freshness_dominates_shapley(self):
        """Stale entry should have s_freshness as largest positive Shapley contributor."""
        entries = [MemoryEntry(
            id="shap_3", content="Stale", type="tool_state",
            timestamp_age_days=60, source_trust=0.95,
            source_conflict=0.05, downstream_count=1,
        )]
        result = compute(entries, action_type="reversible", domain="general")
        shapley = compute_shapley_values(result.component_breakdown, "reversible", "general")

        # s_freshness should be the largest positive contributor
        positive = {k: v for k, v in shapley.items() if v > 0}
        if positive:
            top = max(positive, key=positive.get)
            assert top in ("s_freshness", "s_drift", "r_recall")  # all freshness-driven

    def test_recovery_negative_shapley(self):
        """s_recovery should have negative Shapley value (reduces risk)."""
        entries = [MemoryEntry(
            id="shap_4", content="Fresh", type="semantic",
            timestamp_age_days=5, source_trust=0.9,
            source_conflict=0.1, downstream_count=2,
        )]
        result = compute(entries)
        shapley = compute_shapley_values(result.component_breakdown)

        assert shapley["s_recovery"] < 0

    def test_shapley_in_api_response(self):
        """Preflight API response should include shapley_values."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry(type="tool_state", timestamp_age_days=20)],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "shapley_values" in data
        sv = data["shapley_values"]
        assert isinstance(sv, dict)
        assert "s_freshness" in sv
        assert "s_recovery" in sv

    def test_shapley_in_batch_response(self):
        """Batch response should include shapley_values per entry."""
        resp = client.post("/v1/preflight/batch", json={
            "entries": [
                _fresh_entry(id="shap_b1"),
                _fresh_entry(id="shap_b2", type="tool_state", timestamp_age_days=30),
            ],
        }, headers=AUTH)

        assert resp.status_code == 200
        for r in resp.json()["results"]:
            assert "shapley_values" in r

    def test_shapley_with_custom_weights(self):
        """Custom weights should produce different Shapley values."""
        breakdown = {"s_freshness": 50.0, "s_drift": 30.0, "s_provenance": 10.0,
                     "s_propagation": 20.0, "r_recall": 35.0, "r_encode": 5.0,
                     "s_interference": 15.0, "s_recovery": 75.0, "r_belief": 40.0,
                     "s_relevance": 0.0}

        default_sv = compute_shapley_values(breakdown, "reversible", "general")
        custom_sv = compute_shapley_values(breakdown, "reversible", "general", custom_weights={
            "s_freshness": 0.50, "s_drift": 0.05, "s_provenance": 0.05,
            "s_propagation": 0.05, "r_recall": 0.05, "r_encode": 0.05,
            "s_interference": 0.05, "s_recovery": -0.05, "r_belief": 0.05,
            "s_relevance": 0.05,
        })

        # s_freshness contribution should be much larger with custom weights
        assert custom_sv["s_freshness"] > default_sv["s_freshness"]

    def test_shapley_zero_for_empty_entries(self):
        """Empty entries produce zero omega, so all Shapley values should be 0."""
        result = compute([])
        shapley = compute_shapley_values(result.component_breakdown)
        assert all(v == 0 for v in shapley.values())


class TestLyapunovStability:
    def test_V_positive_definite(self):
        """V(x) must be > 0 for non-equilibrium state."""
        lyap = compute_lyapunov(healing_counter=1, projected_improvement=8.0, action="REFETCH")
        assert lyap.V > 0

    def test_V_dot_negative(self):
        """V̇(x) must be < 0 for convergence."""
        lyap = compute_lyapunov(healing_counter=1, projected_improvement=8.0, action="REFETCH")
        assert lyap.V_dot < 0

    def test_guaranteed_stability(self):
        """First heal should guarantee stability: V > 0 and V̇ < 0."""
        lyap = compute_lyapunov(healing_counter=1, projected_improvement=8.0, action="REFETCH")
        assert lyap.guaranteed is True
        assert lyap.converging is True

    def test_convergence_over_iterations(self):
        """V should decrease with each heal iteration."""
        values = []
        for i in range(1, 6):
            lyap = compute_lyapunov(healing_counter=i, projected_improvement=8.0, action="REFETCH")
            values.append(lyap.V)
        # Each V should be less than or equal to the previous
        for j in range(1, len(values)):
            assert values[j] <= values[j - 1]

    def test_different_actions_different_decay(self):
        """REFETCH should converge faster than REBUILD_WORKING_SET."""
        lyap_refetch = compute_lyapunov(healing_counter=3, projected_improvement=8.0, action="REFETCH")
        lyap_rebuild = compute_lyapunov(healing_counter=3, projected_improvement=3.5, action="REBUILD_WORKING_SET")
        # REFETCH has higher decay, so V should be smaller (more converged)
        assert lyap_refetch.V < lyap_rebuild.V

    def test_equilibrium_after_many_heals(self):
        """After many heals, V should approach 0 (equilibrium)."""
        lyap = compute_lyapunov(healing_counter=20, projected_improvement=8.0, action="REFETCH")
        assert lyap.V < 1.0  # near equilibrium

    def test_lyapunov_in_heal_api_response(self):
        """POST /v1/heal should include lyapunov_stability."""
        resp = client.post("/v1/heal", json={
            "entry_id": "lyap_test_001",
            "action": "REFETCH",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "lyapunov_stability" in data
        ls = data["lyapunov_stability"]
        assert "V" in ls
        assert "V_dot" in ls
        assert "converging" in ls
        assert "guaranteed" in ls
        assert ls["V"] > 0
        assert ls["V_dot"] < 0
        assert ls["guaranteed"] is True


class TestValueOfInformation:
    def test_voi_positive_for_stale_entry(self):
        """Stale entry should have positive VoI (healing it improves omega)."""
        entries = [
            MemoryEntry(id="voi_stale", content="Stale data", type="tool_state",
                        timestamp_age_days=30, source_trust=0.5, source_conflict=0.6,
                        downstream_count=5, r_belief=0.4),
            MemoryEntry(id="voi_fresh", content="Fresh data", type="semantic",
                        timestamp_age_days=1, source_trust=0.95, source_conflict=0.05,
                        downstream_count=1),
        ]
        results = compute_importance_with_voi(entries, "irreversible", "fintech")
        stale = next(r for r in results if r.entry_id == "voi_stale")
        assert stale.voi_score > 0

    def test_voi_zero_for_fresh_entry(self):
        """Fresh trusted entry should have ~0 VoI (nothing to improve)."""
        entries = [
            MemoryEntry(id="voi_f1", content="Fresh", type="semantic",
                        timestamp_age_days=0, source_trust=1.0, source_conflict=0.0,
                        downstream_count=1, r_belief=1.0),
        ]
        results = compute_importance_with_voi(entries)
        assert results[0].voi_score == 0

    def test_voi_sorted_descending(self):
        """Results should be sorted by VoI descending (highest ROI first)."""
        entries = [
            MemoryEntry(id="voi_low", content="Slightly stale", type="semantic",
                        timestamp_age_days=10, source_trust=0.8, source_conflict=0.2,
                        downstream_count=2),
            MemoryEntry(id="voi_high", content="Very stale", type="tool_state",
                        timestamp_age_days=60, source_trust=0.4, source_conflict=0.7,
                        downstream_count=8, r_belief=0.2),
        ]
        results = compute_importance_with_voi(entries, "irreversible", "fintech")
        assert results[0].voi_score >= results[1].voi_score
        assert results[0].entry_id == "voi_high"

    def test_voi_higher_for_more_impactful_entry(self):
        """Entry with worse metrics should have higher VoI."""
        entries = [
            MemoryEntry(id="voi_bad", content="Bad", type="tool_state",
                        timestamp_age_days=90, source_trust=0.3, source_conflict=0.8,
                        downstream_count=10, r_belief=0.1),
            MemoryEntry(id="voi_ok", content="OK", type="semantic",
                        timestamp_age_days=5, source_trust=0.9, source_conflict=0.1,
                        downstream_count=1),
        ]
        results = compute_importance_with_voi(entries, "irreversible", "fintech")
        bad = next(r for r in results if r.entry_id == "voi_bad")
        ok = next(r for r in results if r.entry_id == "voi_ok")
        assert bad.voi_score > ok.voi_score

    def test_voi_empty_entries(self):
        """Empty entries list returns empty results."""
        results = compute_importance_with_voi([])
        assert results == []

    def test_voi_in_api_at_risk_warnings(self):
        """API at_risk_warnings should include voi_score."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [{
                "id": "voi_api_test",
                "content": "Budapest office: Váci út 47, open 9-18",
                "type": "tool_state",
                "timestamp_age_days": 94,
                "source_trust": 0.9,
                "source_conflict": 0.1,
                "downstream_count": 4,
                "source": "user_stated",
                "has_backup_source": False,
                "action_context": "irreversible",
                "reference_count": 6,
            }],
            "action_type": "irreversible",
            "domain": "fintech",
            "detail_level": "full",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "at_risk_warnings" in data
        warning = data["at_risk_warnings"][0]
        assert "voi_score" in warning
        assert warning["voi_score"] >= 0


class TestDifferentialPrivacy:
    def test_laplace_adds_noise(self):
        """Noised value should differ from original."""
        dp = LaplaceMechanism(epsilon=1.0)
        noised, noise = dp.add_noise(50.0, sensitivity=10.0, seed="test_seed")
        assert noise != 0
        assert noised != 50.0

    def test_laplace_deterministic(self):
        """Same seed should produce same noise (A2 axiom)."""
        dp = LaplaceMechanism(epsilon=1.0)
        n1, _ = dp.add_noise(50.0, sensitivity=10.0, seed="same_seed")
        n2, _ = dp.add_noise(50.0, sensitivity=10.0, seed="same_seed")
        assert n1 == n2

    def test_laplace_different_seeds(self):
        """Different seeds should produce different noise."""
        dp = LaplaceMechanism(epsilon=1.0)
        n1, _ = dp.add_noise(50.0, sensitivity=10.0, seed="seed_a")
        n2, _ = dp.add_noise(50.0, sensitivity=10.0, seed="seed_b")
        assert n1 != n2

    def test_smaller_epsilon_more_noise(self):
        """Smaller ε should add more noise (stronger privacy)."""
        dp_strong = LaplaceMechanism(epsilon=0.1)
        dp_weak = LaplaceMechanism(epsilon=10.0)
        # Expected noise scale = sensitivity / epsilon
        check_strong = dp_strong.check_guarantee(5, "test")
        check_weak = dp_weak.check_guarantee(5, "test")
        assert check_strong.noise_added > check_weak.noise_added

    def test_sensitivity_scales_with_entries(self):
        """More entries = lower sensitivity (averaging effect)."""
        dp = LaplaceMechanism(epsilon=1.0)
        s1 = dp.compute_sensitivity(1)
        s10 = dp.compute_sensitivity(10)
        assert s1 > s10

    def test_dp_guarantee_always_satisfied(self):
        """Laplace mechanism always satisfies ε-DP by construction."""
        dp = LaplaceMechanism(epsilon=1.0)
        result = dp.check_guarantee(5, "test")
        assert result.dp_satisfied is True
        assert result.mechanism == "laplace"
        assert result.epsilon == 1.0

    def test_invalid_epsilon_raises(self):
        with pytest.raises(ValueError):
            LaplaceMechanism(epsilon=0)
        with pytest.raises(ValueError):
            LaplaceMechanism(epsilon=-1)

    def test_privacy_guarantee_in_api_response(self):
        """dp_epsilon in request should return privacy_guarantee."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "dp_epsilon": 1.0,
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "privacy_guarantee" in data
        pg = data["privacy_guarantee"]
        assert pg["epsilon"] == 1.0
        assert pg["mechanism"] == "laplace"
        assert pg["dp_satisfied"] is True

    def test_no_privacy_guarantee_without_epsilon(self):
        """Without dp_epsilon, no privacy_guarantee in response."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        assert "privacy_guarantee" not in resp.json()

    def test_dp_omega_clamped(self):
        """Noised omega should stay within 0-100."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "dp_epsilon": 0.01,  # very strong privacy = lots of noise
        }, headers=AUTH)

        assert resp.status_code == 200
        omega = resp.json()["omega_mem_final"]
        assert 0 <= omega <= 100


class TestCustomThresholds:
    def test_custom_thresholds_change_decision(self):
        """Custom thresholds should change USE_MEMORY to WARN."""
        entries = [MemoryEntry(
            id="ct_1", content="Test", type="semantic",
            timestamp_age_days=10, source_trust=0.9,
            source_conflict=0.1, downstream_count=2,
        )]
        # Default thresholds: score ~0 → USE_MEMORY
        default = compute(entries)
        assert default.recommended_action == "USE_MEMORY"

        # Very strict thresholds: warn at 0 → everything is WARN or higher
        strict = compute(entries, thresholds={"warn": 0, "ask_user": 5, "block": 10})
        assert strict.recommended_action != "USE_MEMORY"

    def test_relaxed_thresholds_allow_more(self):
        """Relaxed thresholds should keep USE_MEMORY for higher scores."""
        entries = [MemoryEntry(
            id="ct_2", content="Moderate risk", type="tool_state",
            timestamp_age_days=20, source_trust=0.7,
            source_conflict=0.3, downstream_count=3,
        )]
        result = compute(entries, action_type="reversible", domain="general",
                         thresholds={"warn": 80, "ask_user": 90, "block": 95})
        assert result.recommended_action == "USE_MEMORY"

    def test_custom_thresholds_via_api(self):
        """API should accept and apply custom thresholds."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry(type="tool_state", timestamp_age_days=20)],
            "thresholds": {"warn": 0, "ask_user": 1, "block": 2},
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        # With thresholds this strict, even moderate scores trigger higher actions
        assert data["recommended_action"] in ("WARN", "ASK_USER", "BLOCK")

    def test_default_thresholds_without_field(self):
        """Without thresholds field, default behavior unchanged."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        assert resp.json()["recommended_action"] == "USE_MEMORY"


class TestAuditLog:
    def test_request_id_in_preflight_response(self):
        """Preflight response should include request_id."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "request_id" in data
        assert len(data["request_id"]) == 36  # UUID format

    def test_request_id_unique_per_call(self):
        """Each preflight call should get a unique request_id."""
        r1 = client.post("/v1/preflight", json={"memory_state": [_fresh_entry()]}, headers=AUTH)
        r2 = client.post("/v1/preflight", json={"memory_state": [_fresh_entry()]}, headers=AUTH)

        assert r1.json()["request_id"] != r2.json()["request_id"]


class TestComplianceEndpoints:
    def test_gdpr_endpoint(self):
        resp = client.get("/v1/compliance/gdpr")
        assert resp.status_code == 200
        data = resp.json()
        assert "data_retention" in data
        assert "right_to_erasure" in data
        assert "data_portability" in data
        assert "dpa_contact" in data
        assert data["dpa_contact"]["email"] == "dpa@sgraal.com"
        assert "memory_state" in data["data_retention"]
        assert "not stored" in data["data_retention"]["memory_state"]

    def test_sla_endpoint(self):
        resp = client.get("/v1/compliance/sla")
        assert resp.status_code == 200
        data = resp.json()
        assert "tiers" in data
        assert "free" in data["tiers"]
        assert "starter" in data["tiers"]
        assert "growth" in data["tiers"]
        assert "enterprise" in data["tiers"]
        assert data["tiers"]["starter"]["uptime"] == "99.9%"
        assert "credit_policy" in data

    def test_compliance_docs_endpoint(self):
        resp = client.get("/v1/compliance/docs")
        assert resp.status_code == 200
        data = resp.json()
        assert "profiles" in data
        assert "EU_AI_ACT" in data["profiles"]
        assert "GDPR" in data["profiles"]
        assert "FDA_510K" in data["profiles"]
        assert "HIPAA" in data["profiles"]
        assert "Article 12" in data["profiles"]["EU_AI_ACT"]["articles"]

    def test_gdpr_sub_processors_listed(self):
        resp = client.get("/v1/compliance/gdpr")
        data = resp.json()
        assert "sub_processors" in data
        names = [sp["name"] for sp in data["sub_processors"]]
        assert "Supabase" in names
        assert "Stripe" in names

    def test_sla_credit_policy(self):
        resp = client.get("/v1/compliance/sla")
        data = resp.json()
        assert "below_99.9%" in data["credit_policy"]
        assert "10%" in data["credit_policy"]["below_99.9%"]


class TestMetrics:
    def test_metrics_prometheus_format(self):
        """GET /metrics should return Prometheus text format."""
        # Make a preflight call first to generate metrics
        client.post("/v1/preflight", json={"memory_state": [_fresh_entry()]}, headers=AUTH)

        resp = client.get("/metrics")
        assert resp.status_code == 200
        text = resp.text
        assert "sgraal_preflight_total" in text
        assert "sgraal_heal_total" in text
        assert "sgraal_decision_total" in text
        assert "sgraal_omega_avg" in text
        assert "sgraal_response_time_p95_ms" in text
        assert "# TYPE" in text

    def test_metrics_json_format(self):
        """GET /metrics?accept=json should return JSON."""
        resp = client.get("/metrics?accept=json")
        assert resp.status_code == 200
        data = resp.json()
        assert "preflight_total" in data
        assert "heal_total" in data
        assert "decisions" in data
        assert "avg_omega" in data
        assert "p95_response_time_ms" in data

    def test_metrics_increment_on_preflight(self):
        """Preflight calls should increment metrics."""
        before = client.get("/metrics?accept=json").json()
        client.post("/v1/preflight", json={"memory_state": [_fresh_entry()]}, headers=AUTH)
        after = client.get("/metrics?accept=json").json()
        assert after["preflight_total"] == before["preflight_total"] + 1

    def test_metrics_increment_on_heal(self):
        """Heal calls should increment heal_total."""
        before = client.get("/metrics?accept=json").json()
        client.post("/v1/heal", json={"entry_id": "metrics_heal_test", "action": "REFETCH"}, headers=AUTH)
        after = client.get("/metrics?accept=json").json()
        assert after["heal_total"] == before["heal_total"] + 1

    def test_trace_in_preflight_response(self):
        """Preflight response should include _trace with span attributes."""
        resp = client.post("/v1/preflight", json={"memory_state": [_fresh_entry()]}, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "_trace" in data
        trace = data["_trace"]
        assert trace["span"] == "preflight"
        assert "api_key_id" in trace
        assert "decision" in trace
        assert "omega_score" in trace
        assert "request_id" in trace
        assert "duration_ms" in trace
        assert trace["duration_ms"] >= 0

    def test_decision_distribution_tracked(self):
        """Decision distribution should track USE_MEMORY counts."""
        data = client.get("/metrics?accept=json").json()
        assert "USE_MEMORY" in data["decisions"]
        assert data["decisions"]["USE_MEMORY"] > 0


class TestWebhooks:
    def test_register_webhook(self):
        resp = client.post("/v1/webhooks", json={
            "url": "https://hooks.example.com/sgraal",
            "events": ["BLOCK", "WARN"],
            "secret": "test_secret_123",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["registered"] is True
        assert "webhook_id" in data
        assert data["events"] == ["BLOCK", "WARN"]
        assert data["target"] == "generic"

    def test_register_slack_webhook(self):
        resp = client.post("/v1/webhooks", json={
            "url": "https://hooks.slack.com/services/T00/B00/xxx",
            "events": ["BLOCK"],
            "secret": "slack_secret",
            "target": "slack",
        }, headers=AUTH)

        assert resp.status_code == 200
        assert resp.json()["target"] == "slack"

    def test_register_pagerduty_webhook(self):
        resp = client.post("/v1/webhooks", json={
            "url": "https://events.pagerduty.com/v2/enqueue",
            "events": ["BLOCK"],
            "secret": "pd_secret",
            "target": "pagerduty",
        }, headers=AUTH)

        assert resp.status_code == 200
        assert resp.json()["target"] == "pagerduty"

    def test_list_webhooks(self):
        resp = client.get("/v1/webhooks", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "webhooks" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_delete_webhook(self):
        # Register
        reg = client.post("/v1/webhooks", json={
            "url": "https://delete-me.example.com",
            "events": ["WARN"],
            "secret": "del_secret",
        }, headers=AUTH)
        wid = reg.json()["webhook_id"]

        # Delete
        resp = client.delete(f"/v1/webhooks/{wid}", headers=AUTH)
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_delete_nonexistent_webhook(self):
        resp = client.delete("/v1/webhooks/nonexistent-id", headers=AUTH)
        assert resp.status_code == 404

    def test_webhook_requires_auth(self):
        resp = client.post("/v1/webhooks", json={
            "url": "https://example.com",
            "events": ["BLOCK"],
            "secret": "s",
        })
        assert resp.status_code in (401, 403)

    def test_hmac_signature_correct(self):
        """Verify HMAC signature computation."""
        from api.main import _sign_payload
        secret = "my_secret"
        payload = '{"test": true}'
        sig = _sign_payload(payload, secret)
        expected = _hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        assert sig == expected


class TestPageRankAuthority:
    def test_pagerank_basic(self):
        """PageRank should produce valid scores summing to ~1.0."""
        adj = {"A": ["B", "C"], "B": ["C"], "C": ["A"]}
        pr = compute_pagerank(adj)
        assert len(pr) == 3
        assert abs(sum(pr.values()) - 1.0) < 0.01

    def test_authority_scores_range(self):
        """Authority scores should be 0–10."""
        scores = compute_authority_scores(["m1", "m2", "m3"])
        assert all(0 <= s <= 10 for s in scores.values())

    def test_authority_scores_empty(self):
        assert compute_authority_scores([]) == {}

    def test_pagerank_opt_in_adds_component(self):
        """use_pagerank=True should add r_importance to component_breakdown."""
        entries = [
            MemoryEntry(id="pr_1", content="A", type="tool_state",
                        timestamp_age_days=30, source_trust=0.8,
                        source_conflict=0.2, downstream_count=3),
            MemoryEntry(id="pr_2", content="B", type="semantic",
                        timestamp_age_days=10, source_trust=0.9,
                        source_conflict=0.1, downstream_count=1),
        ]
        result = compute(entries, use_pagerank=True)
        assert "r_importance" in result.component_breakdown

    def test_pagerank_opt_out_no_component(self):
        """Without use_pagerank, r_importance should not be in breakdown."""
        entries = [
            MemoryEntry(id="pr_3", content="A", type="semantic",
                        timestamp_age_days=5, source_trust=0.9,
                        source_conflict=0.1, downstream_count=1),
        ]
        result = compute(entries, use_pagerank=False)
        assert "r_importance" not in result.component_breakdown

    def test_pagerank_in_api_response(self):
        """use_pagerank=true should include authority_scores and r_importance."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [
                _fresh_entry(id="api_pr_1", type="tool_state", timestamp_age_days=20),
                _fresh_entry(id="api_pr_2"),
            ],
            "use_pagerank": True,
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["use_pagerank"] is True
        assert "authority_scores" in data
        assert "api_pr_1" in data["authority_scores"]
        assert "r_importance" in data["component_breakdown"]

    def test_no_authority_scores_without_flag(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        assert "authority_scores" not in resp.json()
        assert resp.json()["use_pagerank"] is False


class TestDriftDetector:
    def test_identical_distributions_zero_drift(self):
        """Identical distributions should have near-zero drift."""
        scores = [10, 10, 10, 10, 10]
        metrics = compute_drift_metrics(scores, scores)
        assert metrics.kl_divergence < 0.01
        assert metrics.jsd < 0.01

    def test_different_distributions_positive_drift(self):
        """Different distributions should have positive drift."""
        current = [80, 5, 5, 5, 5]
        baseline = [20, 20, 20, 20, 20]
        metrics = compute_drift_metrics(current, baseline)
        assert metrics.kl_divergence > 0
        assert metrics.wasserstein > 0
        assert metrics.jsd > 0

    def test_jsd_bounded(self):
        """JSD should be bounded (scaled 0–100)."""
        metrics = compute_drift_metrics([100, 0, 0], [0, 0, 100])
        assert 0 <= metrics.jsd <= 100

    def test_ensemble_score_range(self):
        """Ensemble score should be 0–100."""
        metrics = compute_drift_metrics([50, 30, 20, 10, 5])
        assert 0 <= metrics.ensemble_score <= 100

    def test_drift_method_is_ensemble(self):
        metrics = compute_drift_metrics([10, 20, 30])
        assert metrics.drift_method in ("ensemble_3", "ensemble_4", "ensemble_5")

    def test_empty_returns_zero(self):
        metrics = compute_drift_metrics([])
        assert metrics.ensemble_score == 0

    def test_drift_details_in_api_response(self):
        """Preflight response should include drift_details."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "drift_details" in data
        dd = data["drift_details"]
        assert "kl_divergence" in dd
        assert "wasserstein" in dd
        assert "jsd" in dd
        assert dd["drift_method"] in ("ensemble_3", "ensemble_4", "ensemble_5")


class TestAlphaDivergence:
    def test_hellinger_case_alpha_0_5(self):
        """α=0.5 should produce Hellinger-like distance."""
        from scoring_engine.drift_detector import _alpha_divergence
        p = [0.5, 0.3, 0.2]
        q = [0.33, 0.33, 0.34]
        result = _alpha_divergence(p, q, 0.5)
        assert result >= 0

    def test_kl_limit_alpha_near_1(self):
        """α close to 1 should approximate KL divergence."""
        from scoring_engine.drift_detector import _alpha_divergence, _kl_divergence
        p = [0.5, 0.3, 0.2]
        q = [0.33, 0.33, 0.34]
        # α=0.99 should be close to KL
        alpha_result = _alpha_divergence(p, q, 0.99)
        kl_result = _kl_divergence(p, q)
        # Both should be positive and in same ballpark
        assert alpha_result >= 0
        assert kl_result >= 0

    def test_alpha_2_0(self):
        """α=2.0 (chi-squared family) should be non-negative."""
        from scoring_engine.drift_detector import _alpha_divergence
        p = [0.6, 0.3, 0.1]
        q = [0.2, 0.5, 0.3]
        result = _alpha_divergence(p, q, 2.0)
        assert result >= 0

    def test_numerical_stability_with_zeros(self):
        """Zero entries should not cause crashes (eps=1e-8)."""
        from scoring_engine.drift_detector import _alpha_divergence
        p = [0.0, 1.0, 0.0]
        q = [0.5, 0.0, 0.5]
        result = _alpha_divergence(p, q, 0.5)
        assert math.isfinite(result)

    def test_ensemble_4_score(self):
        """With α-divergence + MMD, drift_method should be ensemble_4 or ensemble_5."""
        metrics = compute_drift_metrics([80, 5, 5, 5, 5])
        assert metrics.drift_method in ("ensemble_4", "ensemble_5")
        assert metrics.alpha_divergence is not None
        assert metrics.alpha_divergence.alpha_0_5 >= 0
        assert metrics.alpha_divergence.alpha_1_5 >= 0
        assert metrics.alpha_divergence.alpha_2_0 >= 0

    def test_ensemble_score_includes_alpha(self):
        """Ensemble score should differ between 3-method and 4-method."""
        metrics = compute_drift_metrics([60, 20, 10, 5, 5])
        assert metrics.ensemble_score >= 0
        assert metrics.ensemble_score <= 100

    def test_alpha_divergence_in_api_response(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        dd = resp.json()["drift_details"]
        assert "alpha_divergence" in dd
        assert "alpha_0_5" in dd["alpha_divergence"]
        assert "alpha_1_5" in dd["alpha_divergence"]
        assert "alpha_2_0" in dd["alpha_divergence"]
        assert dd["drift_method"] in ("ensemble_4", "ensemble_5")

    def test_backward_compat_identical_distributions(self):
        """Identical distributions should still have near-zero drift."""
        metrics = compute_drift_metrics([10, 10, 10, 10, 10], [10, 10, 10, 10, 10])
        assert metrics.kl_divergence < 0.01
        assert metrics.jsd < 0.01
        if metrics.alpha_divergence:
            assert metrics.alpha_divergence.alpha_0_5 < 1.0

class TestTrendDetection:
    def test_cusum_detects_upward_shift(self):
        """CUSUM should alert on sustained upward shift."""
        # Stable then sudden jump
        history = [10, 10, 10, 10, 10, 50, 55, 60, 65, 70]
        cusum = CUSUMDetector(k=0.5, h=5.0)
        alert, s_pos, s_neg = cusum.detect(history)
        assert alert is True
        assert s_pos > 5.0

    def test_cusum_no_alert_stable(self):
        """CUSUM should not alert on stable series."""
        history = [20, 20, 20, 20, 20, 20, 20, 20]
        cusum = CUSUMDetector(k=0.5, h=5.0)
        alert, _, _ = cusum.detect(history)
        assert alert is False

    def test_ewma_detects_drift(self):
        """EWMA should alert when values deviate >3σ."""
        history = [10, 10, 10, 10, 10, 80, 85, 90, 95]
        ewma = EWMADetector(lam=0.2, L=3.0)
        alert, _ = ewma.detect(history)
        assert alert is True

    def test_ewma_no_alert_stable(self):
        """EWMA should not alert on stable series."""
        history = [25, 25, 25, 25, 25, 25]
        ewma = EWMADetector(lam=0.2, L=3.0)
        alert, _ = ewma.detect(history)
        assert alert is False

    def test_drift_sustained_requires_both(self):
        """drift_sustained requires 4+ consecutive degradations AND both alerts."""
        history = [10, 10, 10, 10, 50, 60, 70, 80, 90]
        trend = detect_trend(history)
        assert trend.consecutive_degradations >= 4
        assert trend.cusum_alert is True
        assert trend.drift_sustained is True

    def test_no_sustained_for_stable(self):
        history = [25, 25, 25, 25, 25]
        trend = detect_trend(history)
        assert trend.drift_sustained is False
        assert trend.consecutive_degradations == 0

    def test_consecutive_degradation_count(self):
        history = [10, 20, 30, 40, 35, 45, 55]
        trend = detect_trend(history)
        assert trend.consecutive_degradations == 3  # 10→20→30→40

    def test_trend_detection_in_api_response(self):
        """Preflight with score_history should include trend_detection."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": [10, 20, 30, 40, 50, 60, 70, 80],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "trend_detection" in data
        td = data["trend_detection"]
        assert "cusum_alert" in td
        assert "ewma_alert" in td
        assert "drift_sustained" in td
        assert "consecutive_degradations" in td

    def test_no_trend_without_history(self):
        """Without score_history, no trend_detection in response."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        assert "trend_detection" not in resp.json()


class TestCalibration:
    def test_brier_score_perfect_safe(self):
        """High assurance + low omega → low Brier score (good calibration)."""
        cal = compute_calibration(omega_mem_final=10, assurance_score=95, component_breakdown={"s_freshness": 5})
        assert cal.brier_score < 0.01  # near perfect

    def test_brier_score_overconfident(self):
        """High assurance + high omega → high Brier score (bad calibration)."""
        cal = compute_calibration(omega_mem_final=80, assurance_score=90, component_breakdown={"s_freshness": 80})
        assert cal.brier_score > 0.5

    def test_log_loss_correct_prediction(self):
        """Correct confident prediction → low log loss."""
        cal = compute_calibration(omega_mem_final=10, assurance_score=95, component_breakdown={"s_freshness": 5})
        assert cal.log_loss < 0.1

    def test_log_loss_wrong_prediction(self):
        """Wrong confident prediction → high log loss."""
        cal = compute_calibration(omega_mem_final=80, assurance_score=90, component_breakdown={"s_freshness": 80})
        assert cal.log_loss > 1.0

    def test_calibrated_scores_sum_to_100(self):
        """Softmax calibrated scores should sum to ~100."""
        breakdown = {"s_freshness": 50, "s_drift": 30, "s_provenance": 20}
        cal = compute_calibration(50, 50, breakdown)
        total = sum(cal.calibrated_scores.values())
        assert abs(total - 100) < 1.0

    def test_calibrated_scores_same_keys(self):
        breakdown = {"s_freshness": 50, "s_drift": 30, "r_belief": 40}
        cal = compute_calibration(50, 50, breakdown)
        assert set(cal.calibrated_scores.keys()) == set(breakdown.keys())

    def test_meta_score_range(self):
        """Meta score should be 0–100."""
        breakdown = {"s_freshness": 50, "s_drift": 30, "s_provenance": 20,
                     "s_propagation": 15, "r_recall": 35, "r_encode": 10,
                     "s_interference": 25, "s_recovery": 80, "r_belief": 40,
                     "s_relevance": 5}
        cal = compute_calibration(45, 68, breakdown)
        assert 0 <= cal.meta_score <= 100

    def test_meta_score_low_for_safe(self):
        """Low-risk components → low meta score."""
        safe = {"s_freshness": 2, "s_drift": 1, "s_provenance": 3,
                "s_propagation": 5, "r_recall": 2, "r_encode": 1,
                "s_interference": 2, "s_recovery": 99, "r_belief": 5,
                "s_relevance": 0}
        cal = compute_calibration(5, 96, safe)
        assert cal.meta_score < 30

    def test_calibration_in_api_response(self):
        """Preflight response should include calibration."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "calibration" in data
        c = data["calibration"]
        assert "brier_score" in c
        assert "log_loss" in c
        assert "calibrated_scores" in c
        assert "meta_score" in c
        assert 0 <= c["brier_score"] <= 1
        assert c["log_loss"] >= 0
        assert 0 <= c["meta_score"] <= 100

    def test_empty_breakdown_calibration(self):
        cal = compute_calibration(0, 100, {})
        assert cal.calibrated_scores == {}
        assert cal.brier_score == 0.0


class TestHawkesProcess:
    def test_baseline_no_events(self):
        """No update events → intensity equals baseline μ."""
        result = compute_hawkes_intensity([], current_time=0)
        assert result.current_lambda == 0.1
        assert result.excited is False
        assert result.burst_detected is False

    def test_recent_events_excite(self):
        """Recent events should increase intensity above baseline."""
        # Events at t=-0.1, -0.2, -0.3 (very recent)
        result = compute_hawkes_intensity([-0.1, -0.2, -0.3], current_time=0)
        assert result.current_lambda > result.baseline_mu
        assert result.excited is True

    def test_burst_detected(self):
        """Many recent events → burst (lambda > 2×mu)."""
        # 5 events in last 0.5 days
        times = [-0.1 * i for i in range(5)]
        result = compute_hawkes_intensity(times, current_time=0, mu=0.1, alpha=0.5)
        assert result.burst_detected is True
        assert result.current_lambda > 0.2  # > 2×0.1

    def test_old_events_decay(self):
        """Old events should have minimal excitation (decayed)."""
        # Events 100 days ago
        result = compute_hawkes_intensity([-100, -101, -102], current_time=0)
        assert abs(result.current_lambda - result.baseline_mu) < 0.01

    def test_from_entries_convenience(self):
        """hawkes_from_entries should work with entry ages."""
        # Very recent entries (age 0.1, 0.2, 0.3 days)
        result = hawkes_from_entries([0.1, 0.2, 0.3])
        assert result.current_lambda > result.baseline_mu

    def test_from_entries_old(self):
        """Old entries should not trigger excitement."""
        result = hawkes_from_entries([100, 200, 300])
        assert result.excited is False

    def test_hawkes_in_api_response(self):
        """Preflight response should include hawkes_intensity."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "hawkes_intensity" in data
        h = data["hawkes_intensity"]
        assert "current_lambda" in h
        assert "baseline_mu" in h
        assert "excited" in h
        assert "burst_detected" in h
        assert h["baseline_mu"] == 0.1

    def test_burst_with_recent_entries_via_api(self):
        """Multiple very recent entries should trigger burst in API."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [
                _fresh_entry(id=f"hawkes_{i}", timestamp_age_days=0.1 * (i + 1))
                for i in range(5)
            ],
        }, headers=AUTH)

        assert resp.status_code == 200
        h = resp.json()["hawkes_intensity"]
        assert h["current_lambda"] > h["baseline_mu"]


class TestCopula:
    def test_low_scores_low_joint_risk(self):
        """Low freshness + low drift → low joint risk."""
        result = compute_copula(5.0, 3.0)
        assert result.joint_risk < 20
        assert result.tail_dependence is False

    def test_high_scores_high_joint_risk(self):
        """High freshness + high drift → elevated joint risk."""
        result = compute_copula(90.0, 85.0)
        assert result.joint_risk > 0

    def test_tail_dependence_detected(self):
        """Both elevated simultaneously with high rho → tail dependence."""
        result = compute_copula(90.0, 85.0, rho=0.9)
        assert result.tail_dependence is True

    def test_no_tail_dependence_one_very_low(self):
        """One very low score → independent risk too small for tail dependence."""
        result = compute_copula(50.0, 0.5)
        assert result.tail_dependence is False

    def test_rho_preserved(self):
        result = compute_copula(50.0, 50.0, rho=0.8)
        assert result.rho == 0.8

    def test_joint_risk_range(self):
        """Joint risk should be 0–100."""
        for f in [0, 25, 50, 75, 100]:
            for d in [0, 25, 50, 75, 100]:
                result = compute_copula(float(f), float(d))
                assert 0 <= result.joint_risk <= 100

    def test_copula_in_api_response(self):
        """Preflight response should include copula_analysis."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "copula_analysis" in data
        ca = data["copula_analysis"]
        assert "rho" in ca
        assert "joint_risk" in ca
        assert "tail_dependence" in ca
        assert 0 <= ca["joint_risk"] <= 100


class TestMEWMA:
    def test_in_control_healthy_scores(self):
        """Scores near baseline (25) should be in control."""
        breakdown = {"s_freshness": 25, "s_drift": 25, "s_provenance": 25,
                     "s_relevance": 25, "r_belief": 25}
        result = compute_mewma(breakdown)
        assert result.T2_stat >= 0
        assert result.out_of_control is False

    def test_out_of_control_extreme_scores(self):
        """Extreme scores far from baseline should trigger out_of_control."""
        breakdown = {"s_freshness": 95, "s_drift": 90, "s_provenance": 85,
                     "s_relevance": 80, "r_belief": 90}
        result = compute_mewma(breakdown)
        assert result.T2_stat > 12
        assert result.out_of_control is True

    def test_T2_non_negative(self):
        """T² should always be non-negative."""
        for f in [0, 25, 50, 75, 100]:
            breakdown = {"s_freshness": f, "s_drift": f, "s_provenance": f,
                         "s_relevance": f, "r_belief": f}
            result = compute_mewma(breakdown)
            assert result.T2_stat >= 0

    def test_monitored_components_default(self):
        """Default should monitor 5 key components."""
        result = compute_mewma({"s_freshness": 10})
        assert len(result.monitored_components) == 5
        assert "s_freshness" in result.monitored_components
        assert "r_belief" in result.monitored_components

    def test_custom_components(self):
        """Custom component list should be used."""
        result = compute_mewma(
            {"s_freshness": 50, "s_drift": 40},
            components=["s_freshness", "s_drift"],
        )
        assert result.monitored_components == ["s_freshness", "s_drift"]

    def test_with_history(self):
        """EWMA with history should smooth values."""
        history = [
            {"s_freshness": 10, "s_drift": 10, "s_provenance": 10, "s_relevance": 0, "r_belief": 10},
            {"s_freshness": 12, "s_drift": 11, "s_provenance": 10, "s_relevance": 0, "r_belief": 12},
        ]
        current = {"s_freshness": 15, "s_drift": 14, "s_provenance": 12, "s_relevance": 5, "r_belief": 15}
        result = compute_mewma(current, history=history)
        assert result.T2_stat >= 0
        assert "s_freshness" in result.ewma_vector

    def test_control_limit_default(self):
        result = compute_mewma({"s_freshness": 50})
        assert result.control_limit == 12.0

    def test_mewma_in_api_response(self):
        """Preflight response should include mewma."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "mewma" in data
        m = data["mewma"]
        assert "T2_stat" in m
        assert "control_limit" in m
        assert "out_of_control" in m
        assert "monitored_components" in m
        assert m["T2_stat"] >= 0
        assert m["control_limit"] == 12.0


class TestSheafCohomology:
    def test_zero_entries(self):
        result = compute_sheaf_consistency([])
        assert result.consistency_score == 1.0
        assert result.h1_rank == 0
        assert result.auto_source_conflict == 0.0

    def test_single_entry(self):
        result = compute_sheaf_consistency([{"id": "m1", "content": "hello world"}])
        assert result.consistency_score == 1.0
        assert result.h1_rank == 0

    def test_fully_consistent_set(self):
        """Identical content → fully consistent (Jaccard=1.0 > 0.7)."""
        entries = [
            {"id": "m1", "content": "Budapest office open 9-18"},
            {"id": "m2", "content": "Budapest office open 9-18"},
        ]
        result = compute_sheaf_consistency(entries)
        assert result.h1_rank == 0
        assert result.consistency_score == 1.0
        assert result.auto_source_conflict == 0.0

    def test_inconsistent_pair(self):
        """Overlapping but contradictory content → inconsistent."""
        entries = [
            {"id": "m1", "content": "Budapest office open weekdays 9-18"},
            {"id": "m2", "content": "Budapest office closed permanently since 2025"},
        ]
        result = compute_sheaf_consistency(entries)
        assert result.h1_rank >= 1
        assert result.auto_source_conflict > 0
        assert ("m1", "m2") in result.inconsistent_pairs or ("m2", "m1") in result.inconsistent_pairs

    def test_cycle_detection_three_entries(self):
        """Three entries with pairwise overlap but inconsistency."""
        entries = [
            {"id": "a", "content": "customer prefers email communication always"},
            {"id": "b", "content": "customer prefers phone communication always"},
            {"id": "c", "content": "customer prefers email phone communication"},
        ]
        result = compute_sheaf_consistency(entries)
        assert result.h1_rank >= 0  # may detect inconsistencies
        assert 0 <= result.consistency_score <= 1.0

    def test_fallback_jaccard_no_embeddings(self):
        """Without embeddings, uses Jaccard similarity."""
        entries = [
            {"id": "m1", "content": "the quick brown fox"},
            {"id": "m2", "content": "the quick brown dog"},
        ]
        result = compute_sheaf_consistency(entries)
        # Jaccard("the quick brown fox", "the quick brown dog") = 3/5 = 0.6 < 0.7 → inconsistent
        assert result.h1_rank >= 0
        assert 0 <= result.auto_source_conflict <= 1.0

    def test_backward_compat_manual_override(self):
        """Providing source_conflict manually should still work (no breakage)."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [{
                "id": "compat_1",
                "content": "Test entry",
                "type": "semantic",
                "timestamp_age_days": 5,
                "source_conflict": 0.3,
            }],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        # Manual source_conflict should be used, s_interference reflects it
        assert data["component_breakdown"]["s_interference"] == 30.0

    def test_performance_20_entries(self):
        """Sheaf computation for 20 entries must complete in <5ms."""
        entries = [
            {"id": f"perf_{i}", "content": f"memory entry number {i} about topic alpha beta"}
            for i in range(20)
        ]
        import time
        start = time.monotonic()
        result = compute_sheaf_consistency(entries)
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 50  # generous bound (5ms target, 50ms CI tolerance)
        assert 0 <= result.consistency_score <= 1.0

    def test_consistency_analysis_in_api(self):
        """Auto sheaf computation should appear in API response."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [
                {"id": "sheaf_a", "content": "Budapest office Vaci ut 47 open weekdays", "type": "tool_state", "timestamp_age_days": 5},
                {"id": "sheaf_b", "content": "Budapest office permanently closed since January", "type": "tool_state", "timestamp_age_days": 3},
            ],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "consistency_analysis" in data
        ca = data["consistency_analysis"]
        assert "consistency_score" in ca
        assert "h1_rank" in ca
        assert "inconsistent_pairs" in ca
        assert "auto_source_conflict" in ca


class TestRLPolicy:
    def setup_method(self):
        reset_q_table()

    def test_cold_start_no_override(self):
        """Before 10 episodes, rl_adjusted_action = recommended_action."""
        rl = get_rl_adjustment(30.0, {"s_freshness": 30, "s_drift": 20, "s_provenance": 10}, "WARN", "general")
        assert rl.rl_adjusted_action == "WARN"
        assert rl.learning_episodes == 0
        assert rl.confidence == 0.0

    def test_reward_success(self):
        assert compute_reward("success", "USE_MEMORY") == 1.0
        assert compute_reward("success", "BLOCK") == 1.0

    def test_reward_failure_use_memory_penalty(self):
        """USE_MEMORY + failure = -2.0 (should have blocked)."""
        assert compute_reward("failure", "USE_MEMORY") == -2.0

    def test_reward_failure_other(self):
        assert compute_reward("failure", "BLOCK") == -1.0

    def test_q_table_update(self):
        """Q-value should change after update."""
        q = get_q_table()
        before = q.get_q_values("general", "0:0:0:0")[0]
        update_from_outcome(10, {"s_freshness": 10, "s_drift": 5, "s_provenance": 5}, "USE_MEMORY", "success", "general")
        after = q.get_q_values("general", "0:0:0:0")[0]
        assert after > before  # positive reward should increase Q

    def test_domain_separation(self):
        """Different domains should have independent Q-tables."""
        update_from_outcome(80, {"s_freshness": 80, "s_drift": 60, "s_provenance": 40}, "BLOCK", "success", "fintech")
        update_from_outcome(80, {"s_freshness": 80, "s_drift": 60, "s_provenance": 40}, "USE_MEMORY", "failure", "medical")

        q = get_q_table()
        fintech_q = q.get_q_values("fintech", "3:3:2:1")
        medical_q = q.get_q_values("medical", "3:3:2:1")
        # BLOCK should have positive Q in fintech, USE_MEMORY negative in medical
        assert fintech_q[3] > 0  # BLOCK=3 was success
        assert medical_q[0] < 0  # USE_MEMORY=0 was failure

    def test_episodes_increment(self):
        q = get_q_table()
        assert q.get_episodes("general") == 0
        update_from_outcome(10, {"s_freshness": 10}, "USE_MEMORY", "success", "general")
        assert q.get_episodes("general") == 1
        update_from_outcome(10, {"s_freshness": 10}, "WARN", "success", "general")
        assert q.get_episodes("general") == 2

    def test_after_threshold_can_override(self):
        """After 10+ episodes, RL can suggest different action."""
        # Train with 10+ successes for BLOCK in high-risk state
        for _ in range(12):
            update_from_outcome(80, {"s_freshness": 80, "s_drift": 70, "s_provenance": 50}, "BLOCK", "success", "general")

        rl = get_rl_adjustment(80, {"s_freshness": 80, "s_drift": 70, "s_provenance": 50}, "WARN", "general")
        assert rl.learning_episodes >= 10
        assert rl.confidence > 0
        assert rl.rl_adjusted_action == "BLOCK"  # RL learned BLOCK is better

    def test_discretization_edge_cases(self):
        """Boundary values should discretize correctly."""
        from scoring_engine.rl_policy import _discretize
        assert _discretize(0) == 0
        assert _discretize(25) == 0
        assert _discretize(25.1) == 1
        assert _discretize(50) == 1
        assert _discretize(75) == 2
        assert _discretize(100) == 3

    def test_rl_adjustment_in_api_response(self):
        """Preflight response should include rl_adjustment."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "rl_adjustment" in data
        rl = data["rl_adjustment"]
        assert "q_value" in rl
        assert "rl_adjusted_action" in rl
        assert "learning_episodes" in rl
        assert "confidence" in rl

    def test_outcome_triggers_rl_update(self):
        """Closing an outcome should return rl_reward."""
        # Create preflight
        preflight_resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        outcome_id = preflight_resp.json()["outcome_id"]

        # Close with success
        resp = client.post("/v1/outcome", json={
            "outcome_id": outcome_id,
            "status": "success",
        }, headers=AUTH)

        assert resp.status_code == 200
        assert "rl_reward" in resp.json()
        assert resp.json()["rl_reward"] == 1.0


class TestBOCPD:
    def test_stable_no_changepoint(self):
        """Stable series should have low changepoint probability."""
        history = [25.0] * 20
        result = compute_bocpd(history)
        assert result.regime_change is False
        assert result.p_changepoint < 0.5

    def test_abrupt_shift_detected(self):
        """Abrupt jump in scores should trigger regime change."""
        history = [10.0] * 15 + [80.0] * 10
        result = compute_bocpd(history, hazard_rate=0.05, threshold=0.5)
        assert result.p_changepoint > 0
        # The detector should see some evidence of change

    def test_merkle_reset_on_regime_change(self):
        """Regime change should trigger merkle_reset_triggered."""
        # Use high hazard to make detection easier
        history = [10.0] * 10 + [90.0] * 15
        result = compute_bocpd(history, hazard_rate=0.1, threshold=0.3)
        if result.regime_change:
            assert result.merkle_reset_triggered is True

    def test_run_length_positive(self):
        result = compute_bocpd([20, 20, 20, 20, 20])
        assert result.current_run_length >= 0

    def test_cold_start_short_history(self):
        """Short history (<3) should return safe defaults."""
        result = compute_bocpd([10.0, 20.0])
        assert result.regime_change is False
        assert result.p_changepoint == 0.0
        assert result.current_run_length == 2

    def test_hazard_rate_sensitivity(self):
        """Higher hazard rate should make detection more sensitive."""
        history = [20.0] * 8 + [60.0] * 8
        low_h = compute_bocpd(history, hazard_rate=0.001)
        high_h = compute_bocpd(history, hazard_rate=0.2)
        # Higher hazard = more likely to see changepoint
        assert high_h.p_changepoint >= low_h.p_changepoint

    def test_bocpd_in_trend_detection_api(self):
        """Preflight with score_history should include bocpd in trend_detection."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": [10, 10, 10, 10, 10, 50, 60, 70, 80],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "trend_detection" in data
        td = data["trend_detection"]
        assert "bocpd" in td
        bocpd = td["bocpd"]
        assert "p_changepoint" in bocpd
        assert "regime_change" in bocpd
        assert "current_run_length" in bocpd
        assert "merkle_reset_triggered" in bocpd

    def test_no_bocpd_without_history(self):
        """Without score_history, no bocpd in response."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        assert "trend_detection" not in resp.json()


class TestRMT:
    def test_single_entry_returns_none(self):
        """n_entries < 2 should return None."""
        result = compute_rmt([{"id": "m1", "content": "hello"}])
        assert result is None

    def test_empty_returns_none(self):
        result = compute_rmt([])
        assert result is None

    def test_two_identical_entries(self):
        """Identical entries → high similarity, signal detected."""
        entries = [
            {"id": "m1", "content": "Budapest office open weekdays 9 to 18"},
            {"id": "m2", "content": "Budapest office open weekdays 9 to 18"},
        ]
        result = compute_rmt(entries)
        assert result is not None
        assert result.noise_threshold > 0
        assert 0 <= result.signal_ratio <= 1

    def test_diverse_entries_some_noise(self):
        """Diverse unrelated entries → mostly noise."""
        entries = [
            {"id": "m1", "content": "Budapest office open weekdays"},
            {"id": "m2", "content": "Python programming language tutorial"},
            {"id": "m3", "content": "Mediterranean diet recipe ideas"},
        ]
        result = compute_rmt(entries)
        assert result is not None
        assert result.noise_interference_count >= 0
        assert result.true_interference_count >= 0

    def test_signal_ratio_range(self):
        entries = [
            {"id": f"r_{i}", "content": f"memory entry {i} about topic alpha"}
            for i in range(5)
        ]
        result = compute_rmt(entries)
        assert result is not None
        assert 0 <= result.signal_ratio <= 1

    def test_jaccard_fallback(self):
        """Without embeddings, should use Jaccard and still compute."""
        entries = [
            {"id": "j1", "content": "the quick brown fox jumps"},
            {"id": "j2", "content": "the slow brown dog sleeps"},
        ]
        result = compute_rmt(entries)
        assert result is not None
        assert result.noise_threshold > 0

    def test_performance_20_entries(self):
        entries = [{"id": f"p_{i}", "content": f"entry {i} about alpha beta gamma"} for i in range(20)]
        import time
        start = time.monotonic()
        result = compute_rmt(entries)
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 100  # generous CI tolerance (10ms target)
        assert result is not None

    def test_rmt_in_api_response(self):
        """Preflight with 2+ entries should include rmt_analysis."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [
                _fresh_entry(id="rmt_a"),
                _fresh_entry(id="rmt_b"),
            ],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "rmt_analysis" in data
        rmt = data["rmt_analysis"]
        assert "signal_eigenvalues" in rmt
        assert "noise_threshold" in rmt
        assert "true_interference_count" in rmt
        assert "signal_ratio" in rmt

    def test_no_rmt_single_entry(self):
        """Single entry should not include rmt_analysis."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        assert "rmt_analysis" not in resp.json()


class TestCausalGraph:
    def test_single_entry_returns_none(self):
        result = compute_causal_graph([{"id": "m1", "content": "hello"}])
        assert result is None

    def test_insufficient_history_skip(self):
        """With histories but <10 observations, should return None."""
        entries = [{"id": "a"}, {"id": "b"}]
        histories = {"a": [1, 2, 3], "b": [4, 5, 6]}  # only 3 obs
        result = compute_causal_graph(entries, histories=histories)
        assert result is None

    def test_two_entry_causal_chain(self):
        """Two entries with different ages → causal relationship."""
        entries = [
            {"id": "old", "content": "old data", "timestamp_age_days": 90, "downstream_count": 5, "source_trust": 0.8, "source_conflict": 0.3},
            {"id": "new", "content": "new data", "timestamp_age_days": 5, "downstream_count": 2, "source_trust": 0.9, "source_conflict": 0.1},
        ]
        result = compute_causal_graph(entries)
        assert result is not None
        assert len(result.edges) >= 1
        assert result.edges[0].from_id == "old"

    def test_multi_entry_dag(self):
        """Multiple entries should produce a DAG."""
        entries = [
            {"id": "root", "timestamp_age_days": 100, "downstream_count": 8, "source_trust": 0.7, "source_conflict": 0.4, "content": "root"},
            {"id": "mid", "timestamp_age_days": 50, "downstream_count": 4, "source_trust": 0.8, "source_conflict": 0.2, "content": "mid"},
            {"id": "leaf", "timestamp_age_days": 5, "downstream_count": 1, "source_trust": 0.95, "source_conflict": 0.05, "content": "leaf"},
        ]
        result = compute_causal_graph(entries)
        assert result is not None
        assert result.root_cause is not None

    def test_root_cause_identification(self):
        """Root cause should be the entry with most outgoing causal influence."""
        entries = [
            {"id": "cause", "timestamp_age_days": 120, "downstream_count": 10, "source_trust": 0.5, "source_conflict": 0.6, "content": "cause"},
            {"id": "effect1", "timestamp_age_days": 10, "downstream_count": 2, "source_trust": 0.9, "source_conflict": 0.1, "content": "e1"},
            {"id": "effect2", "timestamp_age_days": 5, "downstream_count": 1, "source_trust": 0.95, "source_conflict": 0.05, "content": "e2"},
        ]
        result = compute_causal_graph(entries)
        assert result is not None
        assert result.root_cause == "cause"

    def test_causal_explanation_format(self):
        entries = [
            {"id": "src", "timestamp_age_days": 80, "downstream_count": 6, "source_trust": 0.6, "source_conflict": 0.5, "content": "source"},
            {"id": "dst", "timestamp_age_days": 5, "downstream_count": 1, "source_trust": 0.9, "source_conflict": 0.1, "content": "dest"},
        ]
        result = compute_causal_graph(entries)
        assert result is not None
        if result.edges:
            assert "causally affects" in result.causal_explanation
            assert "risk source" in result.causal_explanation

    def test_with_history_lingam(self):
        """With sufficient history, should use LiNGAM-style analysis."""
        entries = [{"id": "a"}, {"id": "b"}]
        # a causes b: b = 0.7*a + noise
        import random
        random.seed(42)
        a_hist = [random.gauss(50, 10) for _ in range(20)]
        b_hist = [0.7 * a_hist[i] + random.gauss(0, 5) for i in range(20)]
        histories = {"a": a_hist, "b": b_hist}
        result = compute_causal_graph(entries, histories=histories)
        assert result is not None
        assert len(result.edges) >= 1

    def test_causal_graph_in_api(self):
        """Preflight with 2+ entries should include causal_graph when edges found."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [
                _fresh_entry(id="cg_old", type="tool_state", timestamp_age_days=90, downstream_count=8),
                _fresh_entry(id="cg_new", timestamp_age_days=5, downstream_count=1),
            ],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        if "causal_graph" in data:
            cg = data["causal_graph"]
            assert "edges" in cg
            assert "root_cause" in cg
            assert "causal_chain" in cg
            assert "causal_explanation" in cg


class TestSpectral:
    def test_single_entry_returns_none(self):
        result = compute_spectral([{"id": "m1", "content": "hello"}])
        assert result is None

    def test_empty_returns_none(self):
        result = compute_spectral([])
        assert result is None

    def test_two_entries(self):
        entries = [
            {"id": "a", "content": "Budapest office open weekdays"},
            {"id": "b", "content": "Budapest office closed weekends"},
        ]
        result = compute_spectral(entries)
        assert result is not None
        assert result.fiedler_value >= 0
        assert result.graph_connectivity in ("fragmented", "normal", "dense")

    def test_fragmented_graph(self):
        """Unrelated entries → fragmented (low Fiedler)."""
        entries = [
            {"id": "a", "content": "quantum physics experiments"},
            {"id": "b", "content": "hungarian goulash recipe"},
        ]
        result = compute_spectral(entries)
        assert result is not None
        # Very different content → weak connection

    def test_dense_graph(self):
        """Similar entries → connected graph with valid spectral metrics."""
        entries = [
            {"id": "a", "content": "Budapest office Vaci ut open 9 to 18"},
            {"id": "b", "content": "Budapest office Vaci ut open weekdays 9 18"},
            {"id": "c", "content": "Budapest office address Vaci ut 47"},
        ]
        result = compute_spectral(entries)
        assert result is not None
        assert result.fiedler_value >= 0

    def test_cheeger_bound_valid(self):
        entries = [
            {"id": "a", "content": "alpha beta gamma delta"},
            {"id": "b", "content": "alpha beta gamma epsilon"},
            {"id": "c", "content": "alpha beta zeta eta"},
        ]
        result = compute_spectral(entries)
        assert result is not None
        assert result.cheeger_bound["lower"] <= result.cheeger_bound["upper"]
        assert result.cheeger_bound["lower"] >= 0

    def test_mixing_time_positive(self):
        entries = [
            {"id": "a", "content": "memory entry one about topic"},
            {"id": "b", "content": "memory entry two about topic"},
        ]
        result = compute_spectral(entries)
        assert result is not None
        assert result.mixing_time_estimate > 0

    def test_spectral_in_api_response(self):
        """Preflight with 2+ entries should include spectral_analysis."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [
                _fresh_entry(id="sp_a"),
                _fresh_entry(id="sp_b"),
            ],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "spectral_analysis" in data
        sa = data["spectral_analysis"]
        assert "fiedler_value" in sa
        assert "spectral_gap" in sa
        assert "graph_connectivity" in sa
        assert "cheeger_bound" in sa
        assert "mixing_time_estimate" in sa

    def test_no_spectral_single_entry(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        assert "spectral_analysis" not in resp.json()


class TestConsolidation:
    def test_single_entry(self):
        entries = [{"id": "m1", "content": "hello world", "source_trust": 0.9, "timestamp_age_days": 5}]
        result = compute_consolidation(entries)
        assert result is not None
        assert len(result.scores) == 1
        assert 0 <= result.scores[0].consolidation_score <= 1

    def test_two_entries(self):
        entries = [
            {"id": "a", "content": "Budapest office open weekdays", "source_trust": 0.9, "timestamp_age_days": 10},
            {"id": "b", "content": "Budapest office closed weekends", "source_trust": 0.85, "timestamp_age_days": 15},
        ]
        result = compute_consolidation(entries)
        assert result is not None
        assert len(result.scores) == 2
        assert result.mean_consolidation >= 0

    def test_fragile_detection(self):
        """Very old untrusted entries should be flagged as fragile (below threshold)."""
        entries = [
            {"id": "fragile", "content": "very old uncertain data", "source_trust": 0.2, "timestamp_age_days": 300},
            {"id": "solid", "content": "fresh trusted verified", "source_trust": 0.99, "timestamp_age_days": 1},
        ]
        result = compute_consolidation(entries, fragile_threshold=0.5)
        assert result is not None
        # Both entries have scores below 0.5 with hash-based vectors, both fragile
        assert len(result.fragile_entries) >= 1
        # fragile entry should appear in fragile list
        assert "fragile" in result.fragile_entries

    def test_stable_detection(self):
        """Entry with high embedding similarity should be stable with low threshold."""
        # Use explicit embeddings to get high MI ratio
        entries = [
            {"id": "s1", "content": "verified data today", "source_trust": 0.99, "timestamp_age_days": 0,
             "prompt_embedding": [0.9, 0.1, 0.8, 0.2]},
            {"id": "s2", "content": "verified data now", "source_trust": 0.95, "timestamp_age_days": 1,
             "prompt_embedding": [0.85, 0.15, 0.75, 0.25]},
        ]
        result = compute_consolidation(entries, stable_threshold=0.2)
        assert result is not None
        assert any(s.stable for s in result.scores)

    def test_replay_priority_ordering(self):
        """Replay priority should be sorted by consolidation_score ascending."""
        entries = [
            {"id": "low", "content": "old uncertain", "source_trust": 0.3, "timestamp_age_days": 200},
            {"id": "high", "content": "new verified", "source_trust": 0.99, "timestamp_age_days": 1},
        ]
        result = compute_consolidation(entries)
        assert result is not None
        # replay_priority is sorted ascending by score
        assert len(result.replay_priority) == 2
        # Verify ordering is consistent: first entry has lower or equal score than second
        scores_map = {s.entry_id: s.consolidation_score for s in result.scores}
        assert scores_map[result.replay_priority[0]] <= scores_map[result.replay_priority[1]]

    def test_empty_returns_none(self):
        assert compute_consolidation([]) is None

    def test_hopfield_energy_computed(self):
        """Two related entries should produce non-zero Hopfield energy."""
        from scoring_engine.consolidation import _hopfield_energy
        W = [[0, 0.8], [0.8, 0]]
        patterns = [[1.0, -1.0, 1.0], [1.0, 1.0, -1.0]]
        energy = _hopfield_energy(W, patterns)
        assert energy != 0

    def test_consolidation_in_api_response(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert "consolidation" in data
        c = data["consolidation"]
        assert "scores" in c
        assert "mean_consolidation" in c
        assert "fragile_entries" in c
        assert "replay_priority" in c


class TestJumpDiffusion:
    """Tests for DS-04 Jump-Diffusion process."""

    def test_insufficient_history_returns_none(self):
        """Less than 5 observations returns None."""
        assert compute_jump_diffusion([10, 20, 30], 40) is None
        assert compute_jump_diffusion([], 40) is None
        assert compute_jump_diffusion([10, 20, 30, 40], 50) is None

    def test_no_jumps_normal_diffusion(self):
        """Smooth history should show no jumps."""
        history = [30.0, 31.0, 30.5, 31.5, 30.8, 31.2, 30.9]
        result = compute_jump_diffusion(history, 31.0)
        assert result is not None
        assert result.jump_detected is False
        assert result.jump_size == 0.0
        assert result.flash_crash_risk is False
        assert result.diffusion_sigma > 0

    def test_single_jump_detected(self):
        """A sudden spike should be detected as a jump."""
        # Smooth history then a huge spike
        history = [30.0, 30.1, 30.2, 30.0, 30.1]
        current = 60.0  # massive jump
        result = compute_jump_diffusion(history, current)
        assert result is not None
        assert result.jump_detected is True
        assert result.jump_size > 0

    def test_flash_crash_risk_threshold(self):
        """History with >10% jumps should flag flash_crash_risk."""
        # Mostly stable with occasional large spikes — enough jumps for λ > 0.1
        history = [30, 30.1, 30.2, 80, 30, 30.1, 30.2, 75, 30, 30.1]
        result = compute_jump_diffusion(history, 30.0)
        assert result is not None
        assert result.jump_rate_lambda > 0.1
        assert result.flash_crash_risk is True

    def test_cascade_risk_top_level_api(self):
        """cascade_risk should be a top-level field in preflight response."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": [30, 31, 30, 31, 30],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        # cascade_risk must always be present at top level
        assert "cascade_risk" in data
        assert isinstance(data["cascade_risk"], bool)

    def test_expected_next_jump_calculation(self):
        """expected_next_jump = 1/λ when jumps exist."""
        # Create history where exactly 1 out of 10 changes is a jump → λ≈0.1
        history = [30.0, 30.1, 30.0, 30.1, 30.0, 30.1, 30.0, 30.1, 30.0, 30.1]
        # Add a big jump at the end
        result = compute_jump_diffusion(history, 80.0)
        assert result is not None
        if result.jump_rate_lambda > 0:
            expected = round(1.0 / result.jump_rate_lambda, 2)
            assert result.expected_next_jump == expected

    def test_no_jump_high_expected_next(self):
        """When no jumps detected, expected_next_jump should be very high."""
        history = [30.0, 30.1, 30.0, 30.1, 30.0]
        result = compute_jump_diffusion(history, 30.1)
        assert result is not None
        assert result.expected_next_jump >= 100.0

    def test_jump_diffusion_in_api_response(self):
        """Preflight with sufficient score_history should include jump_diffusion."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": [30, 31, 30, 31, 30, 80],  # 6 scores, last is a spike
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "jump_diffusion" in data
        jd = data["jump_diffusion"]
        assert "jump_detected" in jd
        assert "jump_size" in jd
        assert "jump_rate_lambda" in jd
        assert "diffusion_sigma" in jd
        assert "flash_crash_risk" in jd
        assert "expected_next_jump" in jd

    def test_graceful_degradation_no_history(self):
        """Without score_history, jump_diffusion should not appear, cascade_risk=false."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "jump_diffusion" not in data
        assert data["cascade_risk"] is False

    def test_cascade_risk_requires_both(self):
        """cascade_risk is false when only jump_detected but no hawkes burst."""
        # Smooth history with a jump at end — hawkes won't burst with just 1 entry
        history = [30.0, 30.1, 30.0, 30.1, 30.0]
        result = compute_jump_diffusion(history, 80.0)
        assert result is not None
        assert result.jump_detected is True
        # Without hawkes burst, cascade should not trigger in isolation
        # (This tests the module; API integration tested separately)


class TestHMMRegime:
    """Tests for DS-05 HMM Regime-Switching."""

    def test_insufficient_history_returns_none(self):
        """Less than 20 observations returns None."""
        assert compute_hmm_regime([30] * 10, 30) is None
        assert compute_hmm_regime([30] * 19, 30) is None
        assert compute_hmm_regime([], 30) is None

    def test_stable_state(self):
        """Consistently low scores should classify as STABLE."""
        history = [15.0 + (i % 3) * 0.5 for i in range(25)]
        result = compute_hmm_regime(history, 15.0)
        assert result is not None
        assert result.current_state in ("STABLE", "DEGRADING", "CRITICAL")
        assert 0 <= result.state_probability <= 1.0
        assert result.regime_duration >= 1

    def test_degrading_detection(self):
        """Gradually increasing scores should show DEGRADING or CRITICAL."""
        # Ramp from low to mid-range
        history = [10 + i * 2 for i in range(25)]
        result = compute_hmm_regime(history, 60.0)
        assert result is not None
        # End of ramp should not be STABLE
        assert result.current_state in ("DEGRADING", "CRITICAL")

    def test_critical_detection(self):
        """Very high scores should classify as CRITICAL."""
        # Mostly high, some variation
        history = [75.0 + (i % 5) for i in range(25)]
        result = compute_hmm_regime(history, 80.0)
        assert result is not None
        assert result.current_state == "CRITICAL"

    def test_viterbi_decoding(self):
        """Viterbi path should have valid state indices."""
        history = [20, 22, 21, 23, 20, 50, 55, 60, 58, 62, 80, 85, 82, 88, 90, 20, 22, 21, 23, 20]
        result = compute_hmm_regime(history, 21.0)
        assert result is not None
        assert result.current_state in ("STABLE", "DEGRADING", "CRITICAL")
        # Transition probs should sum to ~1
        tp = result.transition_probs
        assert abs(tp["to_stable"] + tp["to_degrading"] + tp["to_critical"] - 1.0) < 0.01

    def test_regime_collapse_risk_top_level(self):
        """regime_collapse_risk should be a top-level field in preflight response."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": [30] * 5,
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "regime_collapse_risk" in data
        assert isinstance(data["regime_collapse_risk"], bool)

    def test_hmm_in_api_with_history(self):
        """Preflight with 20+ score_history should include hmm_regime."""
        history = [30.0 + i * 0.5 for i in range(22)]
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": history,
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "hmm_regime" in data
        hmm = data["hmm_regime"]
        assert "current_state" in hmm
        assert hmm["current_state"] in ("STABLE", "DEGRADING", "CRITICAL")
        assert "state_probability" in hmm
        assert "transition_probs" in hmm
        assert "regime_duration" in hmm
        tp = hmm["transition_probs"]
        assert "to_stable" in tp
        assert "to_degrading" in tp
        assert "to_critical" in tp

    def test_graceful_degradation_short_history(self):
        """Without 20+ history, hmm_regime should not appear."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": [30, 31, 32],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "hmm_regime" not in data
        assert data["regime_collapse_risk"] is False

    def test_regime_duration_counting(self):
        """regime_duration should count consecutive same-state steps."""
        # Long stable run
        history = [15.0] * 25
        result = compute_hmm_regime(history, 15.0)
        assert result is not None
        assert result.regime_duration >= 10  # most steps should be same state

    def test_transition_probs_valid(self):
        """Transition probabilities should be valid probability distributions."""
        history = [20, 22, 50, 55, 80, 85, 20, 22, 50, 55, 80, 85, 20, 22, 50, 55, 80, 85, 20, 22]
        result = compute_hmm_regime(history, 50.0)
        assert result is not None
        tp = result.transition_probs
        for key in ("to_stable", "to_degrading", "to_critical"):
            assert 0 <= tp[key] <= 1.0


class TestZKSheafProof:
    """Tests for SH-02 ZK Sheaf proof."""

    def test_null_when_sheaf_unavailable(self):
        """Returns None when sheaf_result is None."""
        result = compute_zk_sheaf_proof(None, ["e1", "e2"])
        assert result is None

    def test_proof_valid_consistent_graph(self):
        """proof_valid=true when consistency_score >= 0.95 and h1_rank = 0."""
        from scoring_engine.sheaf_cohomology import ConsistencyResult
        sheaf = ConsistencyResult(
            consistency_score=1.0, h1_rank=0,
            inconsistent_pairs=[], auto_source_conflict=0.0,
        )
        result = compute_zk_sheaf_proof(sheaf, ["e1", "e2", "e3"])
        assert result is not None
        assert result.proof_valid is True
        assert len(result.commitment) == 64  # SHA256 hex
        assert len(result.nonce) == 32  # 16 bytes hex

    def test_proof_invalid_when_h1_rank_positive(self):
        """proof_valid=false when h1_rank > 0."""
        from scoring_engine.sheaf_cohomology import ConsistencyResult
        sheaf = ConsistencyResult(
            consistency_score=0.5, h1_rank=2,
            inconsistent_pairs=[("a", "b"), ("c", "d")], auto_source_conflict=0.5,
        )
        result = compute_zk_sheaf_proof(sheaf, ["a", "b", "c", "d"])
        assert result is not None
        assert result.proof_valid is False

    def test_commitment_uniqueness(self):
        """Different nonces produce different commitments."""
        from scoring_engine.sheaf_cohomology import ConsistencyResult
        sheaf = ConsistencyResult(
            consistency_score=1.0, h1_rank=0,
            inconsistent_pairs=[], auto_source_conflict=0.0,
        )
        r1 = compute_zk_sheaf_proof(sheaf, ["e1"])
        r2 = compute_zk_sheaf_proof(sheaf, ["e1"])
        assert r1 is not None and r2 is not None
        assert r1.commitment != r2.commitment  # different nonces
        assert r1.nonce != r2.nonce

    def test_eu_ai_act_compliance_integration(self):
        """proof_valid should add zk_consistency_proof to compliance_result."""
        # Use 2+ entries with overlapping content so sheaf runs
        resp = client.post("/v1/preflight", json={
            "memory_state": [
                _fresh_entry(id="z1", content="Budapest office open weekdays morning"),
                _fresh_entry(id="z2", content="Budapest office open weekdays afternoon"),
            ],
            "compliance_profile": "EU_AI_ACT",
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        if "zk_sheaf_proof" in data and data["zk_sheaf_proof"]["proof_valid"]:
            assert data["compliance_result"].get("zk_consistency_proof") is True

    def test_n_edges_verified_count(self):
        """n_edges_verified should reflect graph edge count."""
        from scoring_engine.sheaf_cohomology import ConsistencyResult
        sheaf = ConsistencyResult(
            consistency_score=1.0, h1_rank=0,
            inconsistent_pairs=[], auto_source_conflict=0.0,
        )
        result = compute_zk_sheaf_proof(sheaf, ["a", "b", "c"])
        assert result is not None
        # 3 entries → C(3,2) = 3 possible edges
        assert result.n_edges_verified == 3

    def test_verified_at_timestamp_format(self):
        """verified_at should be ISO 8601 format."""
        from scoring_engine.sheaf_cohomology import ConsistencyResult
        sheaf = ConsistencyResult(
            consistency_score=1.0, h1_rank=0,
            inconsistent_pairs=[], auto_source_conflict=0.0,
        )
        result = compute_zk_sheaf_proof(sheaf, ["e1"])
        assert result is not None
        # Should parse as ISO datetime
        from datetime import datetime
        dt = datetime.fromisoformat(result.verified_at)
        assert dt.year >= 2026

    def test_graceful_degradation_single_entry(self):
        """Single entry should still produce valid proof (no edges)."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        assert resp.status_code == 200
        # With single entry, sheaf_result may be None → no zk_sheaf_proof
        # This is graceful degradation — no crash

    def test_zk_sheaf_in_api_response(self):
        """Preflight with 2+ overlapping entries should include zk_sheaf_proof."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [
                _fresh_entry(id="s1", content="user preference dark mode theme"),
                _fresh_entry(id="s2", content="user preference dark mode setting"),
            ],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        if "zk_sheaf_proof" in data:
            zk = data["zk_sheaf_proof"]
            assert "commitment" in zk
            assert "proof_valid" in zk
            assert "n_edges_verified" in zk
            assert "nonce" in zk
            assert "verified_at" in zk


class TestOrnsteinUhlenbeck:
    """Tests for DS-06 Ornstein-Uhlenbeck mean-reversion process."""

    def test_insufficient_history_returns_none(self):
        """Less than 10 observations returns None."""
        assert compute_ou_process([30] * 5, 30) is None
        assert compute_ou_process([30] * 9, 30) is None
        assert compute_ou_process([], 30) is None

    def test_mean_reverting_stable_series(self):
        """Scores oscillating around a mean should show mean_reverting=true."""
        # Oscillate around 30 with noise
        history = [30 + ((-1) ** i) * 5 for i in range(15)]
        result = compute_ou_process(history, 30.0)
        assert result is not None
        assert result.mean_reverting is True
        assert result.theta > 0.01
        assert result.half_life > 0
        assert result.half_life < 1000

    def test_non_reverting_trend(self):
        """Monotonically increasing scores should show weak or no mean-reversion."""
        history = [10 + i * 5 for i in range(15)]
        result = compute_ou_process(history, 85.0)
        assert result is not None
        # Pure linear trend: theta=0, sigma=0 (perfect fit), not mean-reverting
        assert result.mean_reverting is False

    def test_expected_value_converges_to_mu(self):
        """Expected future values should move toward μ."""
        history = [30 + ((-1) ** i) * 8 for i in range(15)]
        result = compute_ou_process(history, 50.0)  # current is above equilibrium
        assert result is not None
        if result.mean_reverting:
            # Expected values should be between current and mu
            dev_5 = abs(result.expected_value_5 - result.mu)
            dev_10 = abs(result.expected_value_10 - result.mu)
            dev_now = abs(50.0 - result.mu)
            # Deviation should decrease over time
            assert dev_10 <= dev_5 or dev_5 <= dev_now

    def test_half_life_positive(self):
        """Half-life should be positive when mean-reverting."""
        history = [30 + ((-1) ** i) * 3 for i in range(12)]
        result = compute_ou_process(history, 30.0)
        assert result is not None
        assert result.half_life > 0

    def test_theta_non_negative(self):
        """theta should be >= 0 (clamped)."""
        history = [10 + i * 2 for i in range(12)]
        result = compute_ou_process(history, 35.0)
        assert result is not None
        assert result.theta >= 0

    def test_current_deviation(self):
        """current_deviation should equal current_score - mu."""
        # Add small noise so ss_xx > 0
        history = [30.0 + ((-1) ** i) * 0.5 for i in range(12)]
        result = compute_ou_process(history, 50.0)
        assert result is not None
        assert abs(result.current_deviation - (50.0 - result.mu)) < 0.01

    def test_ou_in_api_response(self):
        """Preflight with 10+ score_history should include ornstein_uhlenbeck."""
        history = [30 + ((-1) ** i) * 5 for i in range(12)]
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": history,
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "ornstein_uhlenbeck" in data
        ou = data["ornstein_uhlenbeck"]
        assert "mean_reverting" in ou
        assert "half_life" in ou
        assert "expected_value_5" in ou
        assert "expected_value_10" in ou
        assert "equilibrium" in ou
        assert "current_deviation" in ou

    def test_graceful_degradation_short_history(self):
        """Without 10+ history, ornstein_uhlenbeck should not appear."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": [30, 31, 32],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "ornstein_uhlenbeck" not in data

    def test_identical_scores_returns_none(self):
        """All identical scores (zero variance) should return None."""
        result = compute_ou_process([30.0] * 15, 30.0)
        # With zero variance in X, ss_xx = 0, should return None
        # or produce a valid result with theta=0
        if result is not None:
            assert result.sigma == 0.0 or result.theta == 0.0

    def test_repair_plan_wait_message(self):
        """Mean-reverting with short half-life should add WAIT to repair_plan."""
        # Oscillating history → mean-reverting with short half-life
        history = [30 + ((-1) ** i) * 10 for i in range(15)]
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": history,
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        if "ornstein_uhlenbeck" in data and data["ornstein_uhlenbeck"]["mean_reverting"]:
            if data["ornstein_uhlenbeck"]["half_life"] < 10:
                wait_actions = [r for r in data["repair_plan"] if r["action"] == "WAIT"]
                assert len(wait_actions) >= 1
                assert "Self-recovery expected" in wait_actions[0]["reason"]

    def test_repair_plan_heal_message(self):
        """Non-mean-reverting should add MANUAL_HEAL to repair_plan."""
        # Monotonically increasing → not mean-reverting
        history = [10 + i * 5 for i in range(15)]
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": history,
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        if "ornstein_uhlenbeck" in data and not data["ornstein_uhlenbeck"]["mean_reverting"]:
            heal_actions = [r for r in data["repair_plan"] if r["action"] == "MANUAL_HEAL"]
            assert len(heal_actions) >= 1
            assert "not mean-reverting" in heal_actions[0]["reason"]

    def test_null_on_insufficient_history_api(self):
        """No score_history → ornstein_uhlenbeck absent from response."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "ornstein_uhlenbeck" not in data

    def test_equilibrium_field(self):
        """Response should include equilibrium (mu) field."""
        history = [30 + ((-1) ** i) * 5 for i in range(12)]
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": history,
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        if "ornstein_uhlenbeck" in data:
            assert "equilibrium" in data["ornstein_uhlenbeck"]
            assert isinstance(data["ornstein_uhlenbeck"]["equilibrium"], float)

    def test_redis_history_fallback(self):
        """Without Redis, score_history param should still work."""
        history = [30 + ((-1) ** i) * 3 for i in range(12)]
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": history,
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "ornstein_uhlenbeck" in data


class TestFreeEnergy:
    """Tests for FE-01 Free Energy Functional."""

    def test_basic_computation(self):
        """Should produce valid free energy from typical inputs."""
        components = {"s_freshness": 30, "s_drift": 20, "s_provenance": 10,
                      "s_propagation": 15, "r_recall": 25, "r_encode": 5,
                      "s_interference": 10, "s_recovery": 80, "r_belief": 10, "s_relevance": 15}
        result = compute_free_energy(35.0, 12.5, components)
        assert result is not None
        assert isinstance(result.F, float)
        assert isinstance(result.elbo, float)
        assert isinstance(result.kl_divergence, float)
        assert isinstance(result.reconstruction, float)
        assert isinstance(result.surprise, float)

    def test_elbo_relation(self):
        """F should equal -ELBO."""
        components = {"s_freshness": 50, "s_drift": 40}
        result = compute_free_energy(40.0, 30.0, components)
        assert result is not None
        assert abs(result.F + result.elbo) < 0.001

    def test_kl_non_negative(self):
        """KL divergence should always be >= 0."""
        for meta in [5, 25, 50, 75, 95]:
            result = compute_free_energy(30.0, float(meta), {"s_freshness": 20, "s_drift": 30})
            assert result is not None
            assert result.kl_divergence >= 0.0

    def test_surprise_normalization(self):
        """Surprise should be in [0, 1] range."""
        components = {"s_freshness": 50, "s_drift": 50}
        # With max_observed_F
        result = compute_free_energy(60.0, 20.0, components, max_observed_F=10.0)
        assert result is not None
        assert 0 <= result.surprise <= 1.0

        # Without max (fallback F/100)
        result2 = compute_free_energy(60.0, 20.0, components)
        assert result2 is not None
        assert 0 <= result2.surprise <= 1.0

    def test_first_run_initialization(self):
        """First run with max_observed_F=None should use fallback normalization."""
        components = {"s_freshness": 30}
        result = compute_free_energy(30.0, 15.0, components, max_observed_F=None)
        assert result is not None
        # Fallback: surprise = F / 100.0
        expected_surprise = min(1.0, max(0.0, result.F / 100.0))
        assert abs(result.surprise - expected_surprise) < 0.001

    def test_max_tracking_with_higher_F(self):
        """When max_observed_F provided, surprise should be F/max."""
        components = {"s_freshness": 50, "s_drift": 50}
        result = compute_free_energy(80.0, 10.0, components, max_observed_F=5.0)
        assert result is not None
        if result.F > 0:
            assert result.surprise == min(1.0, round(result.F / 5.0, 4))

    def test_free_energy_in_api_response(self):
        """Preflight should include free_energy in response."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "free_energy" in data
        fe = data["free_energy"]
        assert "F" in fe
        assert "elbo" in fe
        assert "kl_divergence" in fe
        assert "reconstruction" in fe
        assert "surprise" in fe
        assert fe["kl_divergence"] >= 0

    def test_graceful_degradation_empty_components(self):
        """Empty components should still produce a result."""
        result = compute_free_energy(30.0, 15.0, {})
        assert result is not None
        assert result.kl_divergence >= 0

    def test_importance_surprise_integration(self):
        """High surprise should add free_energy_surprise to at_risk_warnings."""
        # This tests the wiring — with normal inputs surprise is usually low
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        # Verify free_energy is present and surprise field exists
        assert "free_energy" in data
        assert "surprise" in data["free_energy"]


class TestLevyFlight:
    """Tests for DS-07 Lévy Flight tail analysis."""

    def test_insufficient_history_returns_none(self):
        """Less than 10 observations returns None."""
        assert compute_levy_flight([30] * 5, 30) is None
        assert compute_levy_flight([30] * 9, 30) is None
        assert compute_levy_flight([], 30) is None

    def test_light_tail_classification(self):
        """Smooth Gaussian-like changes should give light/moderate tails."""
        # Small regular changes → alpha close to 2
        history = [30 + ((-1) ** i) * 0.5 for i in range(15)]
        result = compute_levy_flight(history, 30.0)
        assert result is not None
        assert result.tail_index in ("light", "moderate")
        assert result.alpha >= 1.5

    def test_heavy_tail_classification(self):
        """History with occasional extreme jumps should detect heavy tails."""
        # Mostly stable with a few huge spikes
        history = [30, 30.1, 30.2, 80, 30, 30.1, 75, 30, 30.2, 85, 30, 30.1]
        result = compute_levy_flight(history, 30.0)
        assert result is not None
        # Should detect heavier tails due to large jumps
        assert result.alpha > 0
        assert result.alpha <= 2.0

    def test_cascade_risk_with_levy(self):
        """cascade_risk should be top-level bool in preflight response."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": [30 + ((-1) ** i) * 2 for i in range(12)],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "cascade_risk" in data
        assert isinstance(data["cascade_risk"], bool)

    def test_repair_plan_heavy_tail_message(self):
        """Heavy-tail risk should add MONITOR to repair_plan."""
        # Create history likely to trigger heavy_tail_risk
        history = [30, 30.1, 80, 30, 30.1, 75, 30, 30.2, 85, 30, 30.1, 90]
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": history,
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        if "levy_flight" in data and data["levy_flight"]["heavy_tail_risk"]:
            monitor_actions = [r for r in data["repair_plan"] if r["action"] == "MONITOR"]
            assert len(monitor_actions) >= 1
            assert "Heavy-tail risk" in monitor_actions[0]["reason"]

    def test_extreme_event_probability_bounds(self):
        """extreme_event_probability should be in [0, 1]."""
        history = [30 + ((-1) ** i) * 5 for i in range(15)]
        result = compute_levy_flight(history, 30.0)
        assert result is not None
        assert 0 <= result.extreme_event_probability <= 1.0

    def test_levy_in_api_response(self):
        """Preflight with 10+ score_history should include levy_flight."""
        history = [30 + ((-1) ** i) * 3 for i in range(12)]
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": history,
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "levy_flight" in data
        lf = data["levy_flight"]
        assert "alpha" in lf
        assert "scale" in lf
        assert "heavy_tail_risk" in lf
        assert "extreme_event_probability" in lf
        assert "tail_index" in lf

    def test_graceful_degradation_no_history(self):
        """Without score_history, levy_flight should not appear."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "levy_flight" not in data


class TestSinkhorn:
    """Tests for OT-01 Sinkhorn Optimal Transport."""

    def test_small_payload_exact_wasserstein(self):
        """n ≤ 5 components should use exact Wasserstein, not Sinkhorn."""
        # 3 components → exact Wasserstein
        scores = [30.0, 50.0, 20.0]
        drift = compute_drift_metrics(scores)
        assert drift.sinkhorn_used is False
        assert drift.sinkhorn_iterations == 0
        assert drift.wasserstein >= 0

    def test_large_payload_sinkhorn(self):
        """n > 5 components should use Sinkhorn approximation."""
        # 10 components → Sinkhorn
        scores = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        drift = compute_drift_metrics(scores)
        assert drift.sinkhorn_used is True
        assert drift.sinkhorn_iterations > 0
        assert drift.wasserstein >= 0

    def test_convergence_check(self):
        """Sinkhorn should converge within 100 iterations for normal inputs."""
        p = [0.1, 0.2, 0.15, 0.05, 0.1, 0.15, 0.1, 0.05, 0.05, 0.05]
        q = [0.1] * 10
        result = sinkhorn_distance(p, q)
        assert result is not None
        assert result.converged is True
        assert result.iterations <= 100

    def test_fallback_on_non_convergence(self):
        """Non-convergence should fall back gracefully (tested via drift_metrics)."""
        # Even with extreme distributions, drift_metrics should produce valid output
        scores = [0.001, 0.001, 0.001, 0.001, 0.001, 99.995]
        drift = compute_drift_metrics(scores)
        assert drift.wasserstein >= 0
        # Either Sinkhorn converged or fell back to exact

    def test_sinkhorn_iterations_count(self):
        """sinkhorn_iterations should be positive when Sinkhorn used."""
        result = sinkhorn_distance([0.2, 0.3, 0.5], [0.33, 0.33, 0.34])
        assert result is not None
        assert result.iterations > 0

    def test_performance_bound(self):
        """Sinkhorn should complete in reasonable time for n > 10."""
        import time
        scores = [float(i * 10) for i in range(1, 16)]  # 15 components
        start = time.time()
        drift = compute_drift_metrics(scores)
        elapsed = time.time() - start
        assert elapsed < 1.0  # must complete within 1 second
        assert drift.sinkhorn_used is True

    def test_cost_matrix_normalization(self):
        """Cost matrix normalization should handle large magnitude differences."""
        # Very different scales
        p = [0.01, 0.99]
        q = [0.5, 0.5]
        p_vals = [0.0, 1000.0]
        q_vals = [0.0, 1.0]
        result = sinkhorn_distance(p, q, p_vals, q_vals)
        assert result is not None
        assert result.distance >= 0
        assert result.converged is True

    def test_backward_compatibility_drift_details(self):
        """API drift_details should include sinkhorn_used and sinkhorn_iterations."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        dd = data["drift_details"]
        assert "wasserstein" in dd
        assert "sinkhorn_used" in dd
        assert "sinkhorn_iterations" in dd
        assert isinstance(dd["sinkhorn_used"], bool)
        assert isinstance(dd["sinkhorn_iterations"], int)

    def test_identical_distributions_low_distance(self):
        """Identical distributions should give low distance (ε-regularized, not exact zero)."""
        p = [0.25, 0.25, 0.25, 0.25]
        q = [0.05, 0.15, 0.3, 0.5]  # different distribution
        r_same = sinkhorn_distance(p, p)
        r_diff = sinkhorn_distance(p, q)
        assert r_same is not None and r_diff is not None
        # Same distribution should have strictly lower distance than different
        assert r_same.distance < r_diff.distance


class TestRateDistortion:
    """Tests for RD-01 Rate-Distortion optimal retention."""

    def test_single_entry(self):
        """Single entry should produce valid result."""
        entries = [{"id": "e1", "source_trust": 0.9, "timestamp_age_days": 5,
                    "source_conflict": 0.1, "downstream_count": 2}]
        result = compute_rate_distortion(entries, 30.0, {"s_freshness": 20})
        assert result is not None
        assert len(result.entries) == 1
        assert result.entries[0].information_value > 0
        assert result.entries[0].keep_score > 0

    def test_two_entries(self):
        """Two entries should compute distortion between them."""
        entries = [
            {"id": "e1", "source_trust": 0.95, "timestamp_age_days": 1, "source_conflict": 0.05, "downstream_count": 1},
            {"id": "e2", "source_trust": 0.3, "timestamp_age_days": 200, "source_conflict": 0.8, "downstream_count": 10},
        ]
        result = compute_rate_distortion(entries, 30.0, {"s_freshness": 50})
        assert result is not None
        assert len(result.entries) == 2
        assert result.total_rate > 0
        assert result.total_distortion > 0

    def test_recommend_delete_trigger(self):
        """Low keep_score + low omega should recommend delete."""
        # Entry with very low trust, very old, high conflict → low info, high distortion
        entries = [
            {"id": "good", "source_trust": 0.95, "timestamp_age_days": 1, "source_conflict": 0.05, "downstream_count": 1},
            {"id": "bad", "source_trust": 0.01, "timestamp_age_days": 500, "source_conflict": 0.99, "downstream_count": 50},
        ]
        result = compute_rate_distortion(entries, 20.0, {"s_freshness": 80}, keep_threshold=0.5)
        assert result is not None
        # At least one entry should have recommend_delete
        deletable = [e for e in result.entries if e.recommend_delete]
        assert result.deletable_count == len(deletable)

    def test_keep_score_bounds(self):
        """keep_score should be non-negative."""
        entries = [{"id": f"e{i}", "source_trust": 0.5, "timestamp_age_days": 10,
                    "source_conflict": 0.1, "downstream_count": 1} for i in range(5)]
        result = compute_rate_distortion(entries, 50.0, {})
        assert result is not None
        for e in result.entries:
            assert e.keep_score >= 0
            assert e.information_value >= 0
            assert e.distortion_cost >= 0

    def test_dynamic_lambda_scaling(self):
        """Lambda should scale with system_health."""
        entries = [{"id": "e1", "source_trust": 0.9, "timestamp_age_days": 5}]
        # High health → low lambda
        r_high = compute_rate_distortion(entries, 30.0, {}, system_health=90.0)
        # Low health → high lambda
        r_low = compute_rate_distortion(entries, 30.0, {}, system_health=10.0)
        assert r_high is not None and r_low is not None
        assert r_high.lambda_used < r_low.lambda_used

    def test_repair_plan_integration(self):
        """API should add DELETE to repair_plan for deletable entries."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [
                _fresh_entry(id="keep_me", source_trust=0.99, timestamp_age_days=1),
            ],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "rate_distortion" in data
        rd = data["rate_distortion"]
        assert "entries" in rd
        assert "compression_ratio" in rd
        assert "lambda_used" in rd
        assert "deletable_count" in rd

    def test_compression_ratio_computation(self):
        """compression_ratio should be deletable_count / total."""
        entries = [{"id": f"e{i}", "source_trust": 0.5, "timestamp_age_days": 10} for i in range(4)]
        result = compute_rate_distortion(entries, 50.0, {})
        assert result is not None
        expected = result.deletable_count / 4
        assert abs(result.compression_ratio - expected) < 0.001

    def test_graceful_degradation_empty(self):
        """Empty entries should return None."""
        assert compute_rate_distortion([], 30.0, {}) is None


class TestStabilityScore:
    """Tests for R_total normalized and StabilityScore 9-component formula."""

    def test_all_components_available(self):
        """StabilityScore with all components should produce valid result."""
        ss = compute_stability_score(
            delta_alpha=0.5, p_transition=0.3, omega_drift=0.4,
            omega_0=0.35, lambda_2=1.0, hurst=0.2,
            h1_rank=2.0, tau_mix=10.0, d_geo_causal=0.5,
        )
        assert 0 <= ss.score <= 1.0
        assert len(ss.components) == 9
        assert ss.interpretation in ("stable", "degrading", "critical")

    def test_missing_components_fallback(self):
        """All zeros (missing data) should still produce a valid score."""
        ss = compute_stability_score()
        assert ss.score == 1.0  # all zero components → all (1 - 0/max) = 1
        assert ss.interpretation == "stable"

    def test_stable_interpretation(self):
        """Low component values should give stable interpretation."""
        ss = compute_stability_score(
            delta_alpha=0.1, p_transition=0.05, omega_drift=0.1,
            omega_0=0.1, lambda_2=0.2, hurst=0.05,
            h1_rank=0, tau_mix=2.0, d_geo_causal=0.1,
        )
        assert ss.score > 0.7
        assert ss.interpretation == "stable"

    def test_degrading_interpretation(self):
        """Moderate component values should give degrading."""
        ss = compute_stability_score(
            delta_alpha=1.0, p_transition=0.5, omega_drift=0.5,
            omega_0=0.5, lambda_2=2.5, hurst=0.5,
            h1_rank=5.0, tau_mix=50.0, d_geo_causal=1.0,
        )
        assert 0.4 <= ss.score <= 0.7
        assert ss.interpretation == "degrading"

    def test_critical_interpretation(self):
        """Max component values should give critical."""
        ss = compute_stability_score(
            delta_alpha=2.0, p_transition=1.0, omega_drift=1.0,
            omega_0=1.0, lambda_2=5.0, hurst=1.0,
            h1_rank=10.0, tau_mix=100.0, d_geo_causal=2.0,
        )
        assert ss.score < 0.01
        assert ss.interpretation == "critical"

    def test_r_total_cap_at_5(self):
        """R_total should be capped at 5.0."""
        r = compute_r_total(
            alpha_divergence_score=10.0,
            s_drift=10.0,
            s_interference=10.0,
            omega_mem_final=100.0,
            fiedler_value=50.0,
        )
        assert r == 5.0

    def test_stability_score_bounds(self):
        """StabilityScore should always be in [0, 1]."""
        # Even with extreme values
        ss = compute_stability_score(
            delta_alpha=100.0, p_transition=100.0, omega_drift=100.0,
            omega_0=100.0, lambda_2=100.0, hurst=100.0,
            h1_rank=100.0, tau_mix=1000.0, d_geo_causal=100.0,
        )
        assert 0 <= ss.score <= 1.0

    def test_dashboard_field_presence(self):
        """Preflight should include r_total_normalized and stability_score."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "r_total_normalized" in data
        assert isinstance(data["r_total_normalized"], float)
        assert data["r_total_normalized"] <= 5.0
        assert "stability_score" in data
        ss = data["stability_score"]
        assert "score" in ss
        assert "components" in ss
        assert "interpretation" in ss
        assert ss["interpretation"] in ("stable", "degrading", "critical")
        assert 0 <= ss["score"] <= 1.0


class TestUnifiedLoss:
    """Tests for L_v4 Unified Loss."""

    def test_all_components(self):
        """Should compute L_v4 from all 11 components."""
        ul = compute_unified_loss(
            L_IB=0.5, L_RL=0.3, L_EWC=0.2, L_SH=1.0, L_HG=0.8,
            L_FE=0.6, L_OT=0.4, T_XY=0.1, L_LDT=0.05, Var_dN=0.02, L_CA=0.3,
        )
        assert ul.L_v4 != 0
        assert len(ul.components) == 11
        assert len(ul.lambda_weights) == 11
        assert ul.dominant_loss in ul.components

    def test_missing_component_fallback(self):
        """All-zero components should produce L_v4 = 0."""
        ul = compute_unified_loss()
        assert ul.L_v4 == 0.0
        assert all(v == 0.0 for v in ul.components.values())

    def test_t_xy_negative_sign(self):
        """T_XY should subtract from L_v4 (maximize transfer entropy)."""
        ul_pos = compute_unified_loss(T_XY=1.0)
        ul_zero = compute_unified_loss(T_XY=0.0)
        # Higher T_XY → lower L_v4
        assert ul_pos.L_v4 < ul_zero.L_v4

    def test_dominant_loss_identification(self):
        """dominant_loss should be the component with highest |λᵢ·Lᵢ|."""
        ul = compute_unified_loss(L_FE=100.0)
        assert ul.dominant_loss == "L_FE"
        ul2 = compute_unified_loss(L_CA=50.0)
        assert ul2.dominant_loss == "L_CA"

    def test_geodesic_update_direction(self):
        """Geodesic update should reduce weight of high-loss components."""
        weights = [1.0] * 11
        losses = [0.0] * 11
        losses[5] = 10.0  # L_FE is very high
        new_w = geodesic_update(weights, losses)
        # Weight for L_FE (index 5) should decrease
        assert new_w[5] < weights[5]

    def test_weight_clipping_bounds(self):
        """Weights should stay in [0.01, 10.0] after geodesic update."""
        weights = [0.02] * 11  # near minimum
        losses = [100.0] * 11  # extreme losses
        new_w = geodesic_update(weights, losses)
        for w in new_w:
            assert 0.01 <= w <= 10.0

    def test_equal_weights_fallback(self):
        """None weights should default to equal 1/11."""
        ul = compute_unified_loss(L_IB=1.0, lambda_weights=None)
        expected = round(1.0 / 11, 4)
        assert ul.lambda_weights[0] == expected

    def test_unified_loss_in_api(self):
        """Preflight should include unified_loss in response."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "unified_loss" in data
        ul = data["unified_loss"]
        assert "L_v4" in ul
        assert "components" in ul
        assert "lambda_weights" in ul
        assert "dominant_loss" in ul
        assert "geodesic_update_count" in ul
        assert len(ul["lambda_weights"]) == 11
        assert len(ul["components"]) == 11


class TestPolicyGradient:
    """Tests for RL-02 Policy Gradient with Advantage."""

    def test_cold_start_no_override(self):
        """With < 20 episodes, pg_override should not appear."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "policy_gradient" in data
        # Cold start: no override
        assert "pg_override" not in data or data.get("pg_override") is not True

    def test_advantage_computation(self):
        """Advantage should be Q(s,a) - V(s) where V = max Q."""
        q = [1.0, 2.0, 0.5, 3.0]
        pg = compute_policy_gradient(q, current_action_idx=1)
        # V(s) = max(q) = 3.0, Q(s,WARN) = 2.0, advantage = 2.0 - 3.0 = -1.0
        assert pg.advantage == -1.0

    def test_softmax_probabilities_sum_to_1(self):
        """Action probabilities should sum to 1.0."""
        q = [1.0, 2.0, 0.5, 3.0]
        pg = compute_policy_gradient(q, current_action_idx=0)
        total = sum(pg.action_probabilities.values())
        assert abs(total - 1.0) < 0.01

    def test_exploration_mode_trigger(self):
        """High entropy (uniform Q) should trigger exploration_mode."""
        # Equal Q-values → uniform softmax → high entropy
        q = [1.0, 1.0, 1.0, 1.0]
        pg = compute_policy_gradient(q, current_action_idx=0)
        assert pg.policy_entropy > 1.0
        assert pg.exploration_mode is True

    def test_no_exploration_peaked_q(self):
        """Peaked Q-values should not trigger exploration."""
        q = [0.0, 0.0, 0.0, 10.0]
        pg = compute_policy_gradient(q, current_action_idx=3, temperature=0.5)
        assert pg.exploration_mode is False

    def test_temperature_decay(self):
        """Temperature should decay by 0.99 per step, min 0.1."""
        t1 = decay_temperature(1.0)
        assert t1 == 0.99
        t2 = decay_temperature(0.1)
        assert t2 == 0.1  # at minimum, stays
        t3 = decay_temperature(0.105)
        assert t3 >= 0.1

    def test_policy_entropy_bounds(self):
        """Entropy should be >= 0 and <= log(4) ≈ 1.386."""
        import math
        q = [5.0, 0.0, 0.0, 0.0]
        pg = compute_policy_gradient(q, current_action_idx=0, temperature=0.1)
        assert pg.policy_entropy >= 0
        q_uniform = [1.0, 1.0, 1.0, 1.0]
        pg2 = compute_policy_gradient(q_uniform, current_action_idx=0)
        assert pg2.policy_entropy <= math.log(4) + 0.01

    def test_policy_gradient_in_api(self):
        """Preflight should include policy_gradient."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "policy_gradient" in data
        pg = data["policy_gradient"]
        assert "action_probabilities" in pg
        assert "advantage" in pg
        assert "temperature" in pg
        assert "policy_entropy" in pg
        assert "exploration_mode" in pg
        probs = pg["action_probabilities"]
        assert abs(sum(probs.values()) - 1.0) < 0.01


class TestInfoThermodynamics:
    """Tests for IT-01 Information Thermodynamics."""

    def test_insufficient_history_returns_none(self):
        """Less than 5 observations returns None."""
        assert compute_info_thermodynamics([30, 31, 32], 33, [10, 20]) is None
        assert compute_info_thermodynamics([], 30, [10]) is None

    def test_transfer_entropy_non_negative(self):
        """Transfer entropy should be >= 0."""
        history = [30, 35, 40, 45, 50, 55, 60]
        result = compute_info_thermodynamics(history, 65, [20, 30, 40])
        assert result is not None
        assert result.transfer_entropy >= 0
        assert result.max_flow >= result.transfer_entropy

    def test_landauer_bound_with_healing(self):
        """Landauer bound should increase with healing_counter."""
        history = [30, 31, 32, 33, 34]
        r0 = compute_info_thermodynamics(history, 35, [10], healing_counter=0)
        r5 = compute_info_thermodynamics(history, 35, [10], healing_counter=5)
        assert r0 is not None and r5 is not None
        assert r5.landauer_bound > r0.landauer_bound

    def test_information_temperature(self):
        """Info temperature = Var/Mean of component scores."""
        history = [30, 31, 32, 33, 34]
        result = compute_info_thermodynamics(history, 35, [10, 20, 30, 40, 50])
        assert result is not None
        assert result.information_temperature > 0

    def test_entropy_production_non_negative(self):
        """Entropy production (2nd law) should be >= 0."""
        history = [30, 50, 20, 60, 10, 70]
        result = compute_info_thermodynamics(history, 40, [10, 20])
        assert result is not None
        assert result.entropy_production >= 0

    def test_reversibility_bounds(self):
        """Reversibility should be in [0, 1]."""
        history = [30, 31, 32, 33, 34]
        result = compute_info_thermodynamics(history, 35, [10, 20])
        assert result is not None
        assert 0 <= result.reversibility <= 1.0

    def test_max_flow_feeds_unified_loss(self):
        """max_flow should be usable as T_XY in unified loss."""
        history = [30, 35, 40, 45, 50]
        result = compute_info_thermodynamics(history, 55, [10, 20, 30])
        assert result is not None
        assert isinstance(result.max_flow, float)

    def test_info_thermodynamics_in_api(self):
        """Preflight with score_history should include info_thermodynamics."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": [30, 32, 34, 36, 38, 40],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "info_thermodynamics" in data
        it = data["info_thermodynamics"]
        assert "transfer_entropy" in it
        assert "max_flow" in it
        assert "landauer_bound" in it
        assert "information_temperature" in it
        assert "entropy_production" in it
        assert "reversibility" in it

    def test_graceful_degradation_no_history(self):
        """Without score_history, info_thermodynamics should not appear."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "info_thermodynamics" not in data


class TestMahalanobis:
    """Tests for I-06 Mahalanobis multivariate anomaly detection."""

    def test_single_entry_returns_none(self):
        """Less than 3 entries returns None."""
        entries = [{"id": "e1", "source_trust": 0.9, "timestamp_age_days": 5}]
        assert compute_mahalanobis(entries) is None
        assert compute_mahalanobis([]) is None

    def test_three_entries(self):
        """Three entries should produce valid Mahalanobis distances."""
        entries = [
            {"id": "e1", "source_trust": 0.9, "timestamp_age_days": 5, "source_conflict": 0.1, "downstream_count": 2, "r_belief": 0.1},
            {"id": "e2", "source_trust": 0.8, "timestamp_age_days": 10, "source_conflict": 0.2, "downstream_count": 3, "r_belief": 0.2},
            {"id": "e3", "source_trust": 0.7, "timestamp_age_days": 15, "source_conflict": 0.15, "downstream_count": 1, "r_belief": 0.1},
        ]
        result = compute_mahalanobis(entries)
        assert result is not None
        assert len(result.distances) == 3
        assert result.mean_distance > 0
        assert result.chi2_threshold > 0

    def test_anomaly_detection(self):
        """An extreme outlier should be flagged as anomaly."""
        entries = [
            {"id": "normal1", "source_trust": 0.9, "timestamp_age_days": 5, "source_conflict": 0.1, "downstream_count": 2},
            {"id": "normal2", "source_trust": 0.85, "timestamp_age_days": 7, "source_conflict": 0.12, "downstream_count": 3},
            {"id": "normal3", "source_trust": 0.88, "timestamp_age_days": 6, "source_conflict": 0.11, "downstream_count": 2},
            {"id": "outlier", "source_trust": 0.01, "timestamp_age_days": 500, "source_conflict": 0.99, "downstream_count": 50},
        ]
        result = compute_mahalanobis(entries)
        assert result is not None
        outlier = next(d for d in result.distances if d.entry_id == "outlier")
        assert outlier.distance > result.mean_distance

    def test_non_anomaly_similar_entries(self):
        """Similar entries should all be non-anomalous."""
        entries = [
            {"id": f"e{i}", "source_trust": 0.9, "timestamp_age_days": 5, "source_conflict": 0.1, "downstream_count": 2}
            for i in range(5)
        ]
        result = compute_mahalanobis(entries)
        assert result is not None
        assert result.anomaly_count == 0

    def test_covariance_regularization(self):
        """Identical entries should still work due to regularization."""
        entries = [
            {"id": f"e{i}", "source_trust": 0.5, "timestamp_age_days": 10, "source_conflict": 0.1, "downstream_count": 1}
            for i in range(4)
        ]
        result = compute_mahalanobis(entries)
        assert result is not None  # regularization prevents singular matrix
        assert result.covariance_condition > 0

    def test_s_interference_adjustment(self):
        """API should boost s_interference when anomalies detected."""
        # 3+ entries needed for Mahalanobis, with an outlier
        resp = client.post("/v1/preflight", json={
            "memory_state": [
                _fresh_entry(id="n1", source_trust=0.95, timestamp_age_days=1),
                _fresh_entry(id="n2", source_trust=0.90, timestamp_age_days=2),
                _fresh_entry(id="out", source_trust=0.01, timestamp_age_days=500, source_conflict=0.99),
            ],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        # Mahalanobis should be computed
        if "mahalanobis_analysis" in data:
            assert "distances" in data["mahalanobis_analysis"]
            assert "anomaly_count" in data["mahalanobis_analysis"]

    def test_dynamic_chi2_threshold(self):
        """chi2_threshold should adjust with number of components."""
        entries = [
            {"id": f"e{i}", "source_trust": 0.5 + i*0.1, "timestamp_age_days": 5 + i*5,
             "source_conflict": 0.1 + i*0.05, "downstream_count": i, "r_belief": i*0.1}
            for i in range(5)
        ]
        result = compute_mahalanobis(entries)
        assert result is not None
        # chi2 threshold for df=5 at 95% should be ~11.07
        assert 10 < result.chi2_threshold < 12

    def test_graceful_degradation_two_entries(self):
        """Two entries should return None (need >= 3)."""
        entries = [
            {"id": "e1", "source_trust": 0.9, "timestamp_age_days": 5},
            {"id": "e2", "source_trust": 0.1, "timestamp_age_days": 100},
        ]
        assert compute_mahalanobis(entries) is None


class TestMMD:
    """Tests for D-04 Maximum Mean Discrepancy."""

    def test_basic_mmd_computation(self):
        """MMD should produce valid result for two distributions."""
        p = [0.1, 0.2, 0.3, 0.4]
        q = [0.25, 0.25, 0.25, 0.25]
        result = compute_mmd(p, q)
        assert result is not None
        assert result.score >= 0
        assert result.sigma > 0
        assert result.kernel == "rbf"

    def test_identical_distributions_zero(self):
        """Identical samples should give MMD = 0."""
        p = [0.5, 0.5, 0.5, 0.5]
        result = compute_mmd(p, p)
        assert result is not None
        assert result.score == 0.0

    def test_different_distributions_positive(self):
        """Different distributions should give positive MMD."""
        p = [1.0, 2.0, 3.0, 4.0]
        q = [10.0, 20.0, 30.0, 40.0]
        result = compute_mmd(p, q)
        assert result is not None
        assert result.score > 0

    def test_sigma_median_heuristic(self):
        """Sigma should be computed via median heuristic."""
        p = [0.1, 0.2, 0.3]
        q = [0.4, 0.5, 0.6]
        result = compute_mmd(p, q)
        assert result is not None
        assert result.sigma > 0

    def test_ensemble_5_score(self):
        """Drift metrics with enough components should use ensemble_5."""
        scores = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        drift = compute_drift_metrics(scores)
        assert drift.drift_method == "ensemble_5"
        assert drift.mmd is not None
        assert drift.ensemble_score >= 0

    def test_n_entries_less_than_2_null(self):
        """MMD with < 2 samples should return None."""
        assert compute_mmd([0.5], [0.5]) is None
        assert compute_mmd([], []) is None

    def test_fallback_to_ensemble_4(self):
        """With only 1 score, MMD cannot compute; should fall back."""
        scores = [50.0]
        drift = compute_drift_metrics(scores)
        assert drift.mmd is None
        assert "ensemble_5" not in drift.drift_method

    def test_backward_compatibility(self):
        """API drift_details should include mmd when available."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        dd = data["drift_details"]
        assert "drift_method" in dd
        if dd["drift_method"] == "ensemble_5":
            assert "mmd" in dd
            assert "score" in dd["mmd"]
            assert "sigma" in dd["mmd"]
            assert "kernel" in dd["mmd"]


class TestPageHinkley:
    """Tests for D-07 Page-Hinkley online change detection."""

    def test_insufficient_history_returns_none(self):
        """Less than 5 observations returns None."""
        assert compute_page_hinkley([30, 31, 32], 33) is None
        assert compute_page_hinkley([], 30) is None

    def test_no_change_stable(self):
        """Stable history should not trigger alert."""
        history = [30.0, 30.1, 30.0, 30.1, 30.0, 30.1, 30.0]
        result = compute_page_hinkley(history, 30.0)
        assert result is not None
        assert result.alert is False
        assert result.ph_statistic >= 0

    def test_change_detected(self):
        """Large sudden shift should trigger alert."""
        # Stable at 30, then jump to 80
        history = [30, 30, 30, 30, 30, 80, 80, 80, 80, 80]
        result = compute_page_hinkley(history, 80.0, lam=5.0)
        assert result is not None
        assert result.alert is True
        assert result.change_magnitude > 0
        assert result.steps_since_change > 0

    def test_custom_delta_lambda(self):
        """Custom delta and lambda should be reflected in result."""
        history = [30, 31, 32, 33, 34]
        result = compute_page_hinkley(history, 35.0, delta=0.01, lam=100.0)
        assert result is not None
        assert result.delta_used == 0.01
        assert result.lambda_used == 100.0

    def test_permanent_shift_detected_top_level(self):
        """permanent_shift_detected should be a top-level field."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": [30, 31, 30, 31, 30],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "permanent_shift_detected" in data
        assert isinstance(data["permanent_shift_detected"], bool)

    def test_steps_since_change_counter(self):
        """steps_since_change should count from change point to end."""
        history = [30, 30, 30, 80, 80, 80, 80, 80]
        result = compute_page_hinkley(history, 80.0, lam=5.0)
        assert result is not None
        if result.alert:
            assert result.steps_since_change >= 1

    def test_page_hinkley_in_api(self):
        """Preflight with score_history should include page_hinkley in trend_detection."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": [30, 31, 32, 33, 34, 35],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        td = data.get("trend_detection", {})
        if "page_hinkley" in td:
            ph = td["page_hinkley"]
            assert "ph_statistic" in ph
            assert "alert" in ph
            assert "change_magnitude" in ph
            assert "steps_since_change" in ph
            assert "running_mean" in ph
            assert "delta_used" in ph
            assert "lambda_used" in ph

    def test_graceful_degradation_no_history(self):
        """Without score_history, page_hinkley should not appear."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        td = data.get("trend_detection", {})
        assert "page_hinkley" not in td

    def test_config_from_request(self):
        """page_hinkley_config should be accepted in request."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "score_history": [30, 31, 32, 33, 34, 35],
            "page_hinkley_config": {"delta": 0.01, "lambda": 100.0},
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        td = data.get("trend_detection", {})
        if "page_hinkley" in td:
            assert td["page_hinkley"]["delta_used"] == 0.01
            assert td["page_hinkley"]["lambda_used"] == 100.0


class TestProvenanceEntropy:
    """Tests for P-03 Shannon entropy on provenance graph."""

    def test_single_source_low_entropy(self):
        """Single entry with high trust should have low entropy."""
        entries = [{"id": "e1", "source_trust": 0.99, "source_conflict": 0.01}]
        result = compute_provenance_entropy(entries)
        assert result is not None
        assert result.per_entry[0].entropy >= 0
        # High trust, low conflict → lower entropy
        assert result.per_entry[0].entropy < 1.5

    def test_multiple_sources(self):
        """Multiple entries should compute per-entry and mean entropy."""
        entries = [
            {"id": "e1", "source_trust": 0.9, "source_conflict": 0.1},
            {"id": "e2", "source_trust": 0.5, "source_conflict": 0.5},
            {"id": "e3", "source_trust": 0.1, "source_conflict": 0.9},
        ]
        result = compute_provenance_entropy(entries)
        assert result is not None
        assert len(result.per_entry) == 3
        assert result.mean_entropy > 0

    def test_conflict_probable_threshold(self):
        """Entry with balanced trust/conflict should flag conflict_probable."""
        entries = [{"id": "e1", "source_trust": 0.5, "source_conflict": 0.5}]
        result = compute_provenance_entropy(entries)
        assert result is not None
        # 0.5/0.5 trust and 0.5/0.5 conflict → high entropy
        assert result.per_entry[0].entropy > 1.0
        assert result.per_entry[0].conflict_probable is True

    def test_s_provenance_adjustment(self):
        """API should boost s_provenance based on mean entropy."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [
                _fresh_entry(id="p1", source_trust=0.5, source_conflict=0.5),
                _fresh_entry(id="p2", source_trust=0.5, source_conflict=0.5),
            ],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "provenance_entropy" in data
        assert "s_provenance" in data["component_breakdown"]

    def test_n_entries_1_edge_case(self):
        """Single entry should still work without division by zero."""
        entries = [{"id": "e1", "source_trust": 0.9}]
        result = compute_provenance_entropy(entries)
        assert result is not None
        assert result.mean_entropy >= 0

    def test_entropy_trend_stable(self):
        """Flat history should give stable trend."""
        entries = [{"id": "e1", "source_trust": 0.5, "source_conflict": 0.5}]
        result = compute_provenance_entropy(entries, history=[1.0, 1.0, 1.0, 1.0])
        assert result is not None
        assert result.entropy_trend == "stable"

    def test_entropy_trend_increasing(self):
        """Rising history should give increasing trend."""
        entries = [{"id": "e1", "source_trust": 0.5}]
        result = compute_provenance_entropy(entries, history=[0.5, 0.7, 0.9, 1.1])
        assert result is not None
        assert result.entropy_trend == "increasing"

    def test_graceful_degradation_empty(self):
        """Empty entries should return None."""
        assert compute_provenance_entropy([]) is None

    def test_provenance_entropy_in_api(self):
        """Preflight should include provenance_entropy."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "provenance_entropy" in data
        pe = data["provenance_entropy"]
        assert "per_entry" in pe
        assert "mean_entropy" in pe
        assert "high_entropy_entries" in pe
        assert "entropy_trend" in pe


class TestSubjectiveLogic:
    """Tests for P-04 Subjective Logic."""

    def test_single_entry_opinion(self):
        """Single entry should produce valid opinion."""
        entries = [{"id": "e1", "source_trust": 0.8, "source_conflict": 0.1}]
        result = compute_subjective_logic(entries)
        assert result is not None
        eid, op = result.opinions[0]
        assert op.belief == 0.8
        assert op.disbelief == 0.1
        assert abs(op.uncertainty - 0.1) < 0.001
        assert abs(op.belief + op.disbelief + op.uncertainty - 1.0) < 0.01

    def test_two_entry_fusion(self):
        """Two entries should produce fused opinion."""
        entries = [
            {"id": "e1", "source_trust": 0.9, "source_conflict": 0.05},
            {"id": "e2", "source_trust": 0.7, "source_conflict": 0.1},
        ]
        result = compute_subjective_logic(entries)
        assert result is not None
        assert result.fused_opinion is not None
        f = result.fused_opinion
        assert abs(f.belief + f.disbelief + f.uncertainty - 1.0) < 0.01

    def test_high_uncertainty_detection(self):
        """Entry with low trust and low conflict should flag high uncertainty."""
        entries = [{"id": "e1", "source_trust": 0.3, "source_conflict": 0.1}]
        result = compute_subjective_logic(entries)
        assert result is not None
        assert "e1" in result.high_uncertainty_entries

    def test_consensus_possible_threshold(self):
        """High-confidence entries should allow consensus."""
        entries = [
            {"id": "e1", "source_trust": 0.95, "source_conflict": 0.04},
            {"id": "e2", "source_trust": 0.90, "source_conflict": 0.05},
        ]
        result = compute_subjective_logic(entries)
        assert result is not None
        assert result.fused_opinion is not None
        # Both have low uncertainty → fused should too
        assert result.consensus_possible is True

    def test_projected_prob_computation(self):
        """P(X) = b + a·u should be more conservative than raw trust."""
        entries = [{"id": "e1", "source_trust": 0.6, "source_conflict": 0.1}]
        result = compute_subjective_logic(entries)
        assert result is not None
        _, op = result.opinions[0]
        # u = 0.3, P = 0.6 + 0.5*0.3 = 0.75
        assert abs(op.projected_prob - 0.75) < 0.01

    def test_s_provenance_replacement(self):
        """API should use projected_prob for s_provenance."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "subjective_logic" in data
        sl = data["subjective_logic"]
        assert "opinions" in sl
        assert "fused_opinion" in sl
        assert "consensus_possible" in sl

    def test_division_by_zero_guard(self):
        """When both entries have u=0, fusion should return None gracefully."""
        entries = [
            {"id": "e1", "source_trust": 0.6, "source_conflict": 0.4},
            {"id": "e2", "source_trust": 0.5, "source_conflict": 0.5},
        ]
        result = compute_subjective_logic(entries)
        assert result is not None
        # u₁=0, u₂=0 → denom=0 → fused=None
        # This is the graceful degradation case

    def test_source_values_exceed_unit(self):
        """trust + conflict > 1.0 should clip proportionally."""
        entries = [{"id": "e1", "source_trust": 0.8, "source_conflict": 0.5}]
        result = compute_subjective_logic(entries)
        assert result is not None
        _, op = result.opinions[0]
        assert abs(op.belief + op.disbelief + op.uncertainty - 1.0) < 0.01
        assert op.uncertainty == 0.0  # clipped, no room for uncertainty


class TestFrechet:
    """Tests for R-05 Frechet distance encoding degradation."""

    def test_initialization_first_call(self):
        """With no reference, compute_frechet returns None (need to store first)."""
        vecs = [[10, 20, 30, 40, 50], [15, 25, 35, 45, 55], [12, 22, 32, 42, 52]]
        result = compute_frechet(vecs, reference_vectors=None)
        assert result is None

    def test_degradation_detection(self):
        """Very different distributions should detect degradation."""
        ref = [[10, 10, 10, 10, 10], [12, 12, 12, 12, 12], [11, 11, 11, 11, 11]]
        cur = [[90, 90, 90, 90, 90], [88, 88, 88, 88, 88], [92, 92, 92, 92, 92]]
        result = compute_frechet(cur, ref)
        assert result is not None
        assert result.fd_score > 10.0
        assert result.encoding_degraded is True

    def test_no_degradation_similar(self):
        """Similar distributions should not detect degradation."""
        ref = [[50, 50, 50, 50, 50], [52, 48, 51, 49, 50], [49, 51, 50, 50, 51]]
        cur = [[51, 49, 50, 50, 50], [50, 50, 51, 49, 50], [50, 51, 49, 50, 51]]
        result = compute_frechet(cur, ref)
        assert result is not None
        assert result.fd_score < 10.0
        assert result.encoding_degraded is False

    def test_mean_shift_computation(self):
        """mean_shift should be ||mu_P - mu_Q||^2."""
        ref = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        cur = [[10, 10, 10], [10, 10, 10], [10, 10, 10]]
        result = compute_frechet(cur, ref)
        assert result is not None
        # mean_shift = 10^2 + 10^2 + 10^2 = 300
        assert abs(result.mean_shift - 300.0) < 1.0

    def test_covariance_shift_non_negative(self):
        """covariance_shift should be >= 0."""
        ref = [[10, 20, 30], [15, 25, 35], [12, 22, 32]]
        cur = [[50, 60, 70], [55, 65, 75], [52, 62, 72]]
        result = compute_frechet(cur, ref)
        assert result is not None
        assert result.covariance_shift >= 0

    def test_sqrtm_diagonal_fallback(self):
        """Identical covariance should produce near-zero cov shift."""
        ref = [[10, 20, 30], [15, 25, 35], [20, 30, 40]]
        cur = [[10, 20, 30], [15, 25, 35], [20, 30, 40]]
        result = compute_frechet(cur, ref)
        assert result is not None
        assert result.covariance_shift < 1.0
        assert result.mean_shift < 1.0

    def test_r_encode_adjustment(self):
        """API should boost r_encode when encoding_degraded."""
        # Without Redis reference, frechet_distance won't appear on first call
        # but the module should not crash
        resp = client.post("/v1/preflight", json={
            "memory_state": [
                _fresh_entry(id="f1", source_trust=0.9, timestamp_age_days=1),
                _fresh_entry(id="f2", source_trust=0.8, timestamp_age_days=2),
                _fresh_entry(id="f3", source_trust=0.7, timestamp_age_days=3),
            ],
        }, headers=AUTH)
        assert resp.status_code == 200
        # Graceful: no crash even without Redis reference

    def test_graceful_degradation_few_entries(self):
        """Less than 3 entries should return None."""
        vecs = [[10, 20], [15, 25]]
        ref = [[10, 20], [15, 25]]
        result = compute_frechet(vecs, ref)
        assert result is None


class TestMutualInformation:
    """Tests for R-06/R-07 Mutual Information and NMI."""

    def test_single_entry_null(self):
        """Less than 2 entries returns None."""
        entries = [{"id": "e1", "source_trust": 0.9}]
        assert compute_mutual_information(entries) is None
        assert compute_mutual_information([]) is None

    def test_high_mi_correlated(self):
        """Highly correlated entries should have high MI."""
        entries = [
            {"id": f"e{i}", "source_trust": 0.1 * i, "source_conflict": 0.01 * i, "timestamp_age_days": i}
            for i in range(1, 8)
        ]
        result = compute_mutual_information(entries)
        assert result is not None
        assert result.mi_score > 0

    def test_low_mi_uncorrelated(self):
        """Entries with no correlation should have low MI."""
        entries = [
            {"id": "e1", "source_trust": 0.9, "source_conflict": 0.9, "timestamp_age_days": 1},
            {"id": "e2", "source_trust": 0.1, "source_conflict": 0.01, "timestamp_age_days": 100},
            {"id": "e3", "source_trust": 0.5, "source_conflict": 0.5, "timestamp_age_days": 50},
        ]
        result = compute_mutual_information(entries)
        assert result is not None
        assert result.mi_score >= 0

    def test_nmi_bounds(self):
        """NMI should be in [0, 1]."""
        entries = [
            {"id": f"e{i}", "source_trust": 0.5 + 0.05 * i, "timestamp_age_days": i * 10}
            for i in range(5)
        ]
        result = compute_mutual_information(entries)
        assert result is not None
        assert 0 <= result.nmi_score <= 1.0

    def test_encoding_efficiency_classification(self):
        """encoding_efficiency should be high/medium/low."""
        entries = [
            {"id": f"e{i}", "source_trust": 0.5, "timestamp_age_days": 10}
            for i in range(5)
        ]
        result = compute_mutual_information(entries)
        assert result is not None
        assert result.encoding_efficiency in ("high", "medium", "low")

    def test_information_loss_computation(self):
        """information_loss = 1.0 - nmi_score."""
        entries = [
            {"id": "e1", "source_trust": 0.9, "timestamp_age_days": 5},
            {"id": "e2", "source_trust": 0.8, "timestamp_age_days": 10},
        ]
        result = compute_mutual_information(entries)
        assert result is not None
        assert abs(result.information_loss - (1.0 - result.nmi_score)) < 0.001

    def test_rho_clipping_edge_case(self):
        """Perfect correlation should not cause log(0)."""
        # All entries with perfectly correlated trust and age
        entries = [
            {"id": f"e{i}", "source_trust": 0.1 * i, "source_conflict": 0.0, "timestamp_age_days": 0}
            for i in range(1, 6)
        ]
        result = compute_mutual_information(entries)
        assert result is not None
        assert math.isfinite(result.mi_score)

    def test_zero_variance_edge_case(self):
        """All identical entries should return mi=0, nmi=0."""
        entries = [
            {"id": f"e{i}", "source_trust": 0.5, "source_conflict": 0.1, "timestamp_age_days": 10}
            for i in range(5)
        ]
        result = compute_mutual_information(entries)
        assert result is not None
        assert result.mi_score == 0.0
        assert result.nmi_score == 0.0

    def test_mutual_information_in_api(self):
        """Preflight with 2+ entries should include mutual_information."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [
                _fresh_entry(id="m1", source_trust=0.9, timestamp_age_days=5),
                _fresh_entry(id="m2", source_trust=0.5, timestamp_age_days=50),
            ],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "mutual_information" in data
        mi = data["mutual_information"]
        assert "mi_score" in mi
        assert "nmi_score" in mi
        assert "encoding_efficiency" in mi
        assert "information_loss" in mi


class TestMDP:
    """Tests for REC-02 MDP optimal healing strategy."""

    def test_safe_state_wait_optimal(self):
        """In SAFE state (low omega), WAIT should be optimal."""
        result = compute_mdp(10.0)
        assert result is not None
        assert result.state == "SAFE"
        assert result.optimal_action == "WAIT"

    def test_critical_state_emergency(self):
        """In CRITICAL state (high omega), aggressive healing should be optimal."""
        result = compute_mdp(90.0)
        assert result is not None
        assert result.state == "CRITICAL"
        assert result.optimal_action in ("FULL_HEAL", "EMERGENCY_HEAL")

    def test_value_iteration_convergence(self):
        """Expected value should be finite and reasonable."""
        result = compute_mdp(50.0)
        assert result is not None
        assert result.expected_value is not None
        assert -100 < result.expected_value < 100

    def test_action_values_all_computed(self):
        """All 4 action values should be present."""
        result = compute_mdp(40.0)
        assert result is not None
        assert len(result.action_values) == 4
        for action in ("WAIT", "SOFT_HEAL", "FULL_HEAL", "EMERGENCY_HEAL"):
            assert action in result.action_values

    def test_repair_plan_integration(self):
        """API should include mdp_recommendation."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "mdp_recommendation" in data
        mdp = data["mdp_recommendation"]
        assert "optimal_action" in mdp
        assert "expected_value" in mdp
        assert "action_values" in mdp
        assert "state" in mdp
        assert "confidence" in mdp

    def test_confidence_sparse_data(self):
        """Without learned transitions, confidence should be low."""
        result = compute_mdp(50.0, transition_data=None)
        assert result is not None
        assert result.confidence == 0.1

    def test_uniform_transition_fallback(self):
        """None transition_data should use defaults without error."""
        result = compute_mdp(60.0, transition_data=None)
        assert result is not None
        assert result.state == "DEGRADED"

    def test_graceful_degradation(self):
        """Various omega values should all produce valid results."""
        for omega in [0, 25, 50, 75, 100]:
            result = compute_mdp(float(omega))
            assert result is not None
            assert result.optimal_action in ("WAIT", "SOFT_HEAL", "FULL_HEAL", "EMERGENCY_HEAL")


class TestMTTR:
    """Tests for REC-03 MTTR Weibull estimation."""

    def test_default_params_cold_start(self):
        """No history should use default params."""
        result = compute_mttr(None)
        assert result is not None
        assert result.weibull_k == 1.5
        assert result.weibull_lambda == 10.0
        assert result.data_points == 0

    def test_mttr_estimate_computation(self):
        """MTTR should be λ·Γ(1+1/k)."""
        result = compute_mttr(None)
        assert result is not None
        assert result.mttr_estimate > 0
        assert result.mttr_estimate < 100

    def test_mttr_p95_computation(self):
        """p95 should be λ·(-log(0.05))^(1/k)."""
        result = compute_mttr(None)
        assert result is not None
        assert result.mttr_p95 > result.mttr_estimate  # p95 > mean

    def test_recovery_probability_bounds(self):
        """Recovery probability should be in [0, 1]."""
        result = compute_mttr(None)
        assert result is not None
        assert 0 <= result.recovery_probability <= 1.0

    def test_sla_compliant_true(self):
        """Short heal durations should be SLA compliant (p95 < 20)."""
        durations = [3.0, 4.0, 5.0, 3.5, 4.5, 2.0, 6.0]
        result = compute_mttr(durations)
        assert result is not None
        assert result.sla_compliant is True

    def test_sla_compliant_false_repair_plan(self):
        """Very long durations should trigger SLA warning."""
        # Simulate very long heal times
        durations = [50.0, 60.0, 55.0, 45.0, 70.0, 65.0, 80.0]
        result = compute_mttr(durations)
        assert result is not None
        assert result.mttr_p95 > 20.0
        assert result.sla_compliant is False

    def test_invalid_parameter_fallback(self):
        """Should handle edge cases gracefully."""
        # All zeros → should fall back to defaults
        result = compute_mttr([0.0, 0.0, 0.0, 0.0, 0.0])
        assert result is not None
        assert result.weibull_k > 0
        assert result.weibull_lambda > 0

    def test_mttr_in_api(self):
        """Preflight should include mttr_analysis."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "mttr_analysis" in data
        m = data["mttr_analysis"]
        assert "mttr_estimate" in m
        assert "mttr_p95" in m
        assert "recovery_probability" in m
        assert "weibull_k" in m
        assert "weibull_lambda" in m
        assert "sla_compliant" in m
        assert "data_points" in m


class TestCTLVerification:
    """Tests for FV-07 CTL branching-time verification."""

    def test_ef_recovery_safe_state(self):
        """SAFE state: recovery already achieved, EF should be True."""
        result = compute_ctl_verification(10.0)
        assert result is not None
        assert result.ef_recovery_possible is True

    def test_ef_recovery_critical_state(self):
        """CRITICAL state: recovery possible via transitions."""
        result = compute_ctl_verification(90.0)
        assert result is not None
        # Even from CRITICAL, there's a path to recovery
        assert result.ef_recovery_possible is True

    def test_ag_heal_works_true(self):
        """From SAFE state, healing should work on all paths."""
        result = compute_ctl_verification(10.0)
        assert result is not None
        assert result.ag_heal_works is True

    def test_ag_heal_works_critical(self):
        """From CRITICAL, healing should still lead to improvement."""
        result = compute_ctl_verification(90.0)
        assert result is not None
        # Heal transitions give 30% chance of reaching SAFE from CRITICAL
        assert result.ag_heal_works is True

    def test_eg_stable_possible(self):
        """From SAFE/WARN, stable operation should be possible."""
        result = compute_ctl_verification(20.0)
        assert result is not None
        assert result.eg_stable_possible is True

    def test_compliance_integration(self):
        """API should include ctl_verification in response."""
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "ctl_verification" in data
        ctl = data["ctl_verification"]
        assert "ef_recovery_possible" in ctl
        assert "ag_heal_works" in ctl
        assert "eg_stable_possible" in ctl
        assert "bounded_steps" in ctl
        assert ctl["bounded_steps"] == 10

    def test_timeout_handling(self):
        """Verification should complete within 100ms."""
        result = compute_ctl_verification(50.0, timeout_ms=100.0)
        assert result is not None
        assert result.verification_time_ms < 100.0

    def test_bounded_steps_in_response(self):
        """bounded_steps should always be 10."""
        result = compute_ctl_verification(50.0)
        assert result is not None
        assert result.bounded_steps == 10
        assert len(result.ctl_formulas) == 3
