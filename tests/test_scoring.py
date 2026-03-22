import sys
import os
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring_engine import compute, MemoryEntry

# Patch out external services before importing the app
with patch.dict(os.environ, {}, clear=False):
    from fastapi.testclient import TestClient
    from api.main import app, API_KEYS, verify_api_key, TIER_LIMITS

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
