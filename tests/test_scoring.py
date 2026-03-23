import sys
import os
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring_engine import compute, MemoryEntry, HealingAction, HealingPolicy, load_healing_policies, compute_importance, ComplianceEngine, ComplianceProfile, HealingPolicyMatrix, PolicyVerifier

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
