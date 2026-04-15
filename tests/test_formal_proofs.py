"""Tests for formal proofs: weight normalization, healing termination, A2 axiom."""
import sys, os, math, random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring_engine import compute, MemoryEntry
from scoring_engine.omega_mem import WEIGHTS


# ---------------------------------------------------------------------------
# #619: Weight Normalization Theorem
# ---------------------------------------------------------------------------

class TestWeightNormalization:
    def test_random_vectors_bounded(self):
        """10,000 random component vectors → omega always in [0, 100]."""
        for seed in range(10000):
            rng = random.Random(seed)
            entries = [MemoryEntry(
                id=f"wn_{seed}", content=f"Content {seed}",
                type=rng.choice(["semantic", "tool_state", "episodic"]),
                timestamp_age_days=rng.uniform(0, 500),
                source_trust=rng.uniform(0.01, 0.99),
                source_conflict=rng.uniform(0.01, 0.99),
                downstream_count=rng.randint(0, 100),
                r_belief=rng.uniform(0.01, 0.99),
            )]
            result = compute(entries, "reversible", "general")
            assert 0 <= result.omega_mem_final <= 100, \
                f"seed={seed}: omega={result.omega_mem_final} out of [0,100]"

    def test_handtuned_weights_valid(self):
        """Hand-tuned WEIGHTS dict has S = Σ|wᵢ| > 0."""
        S = sum(abs(w) for w in WEIGHTS.values())
        assert S > 0, f"Weight sum S={S} must be positive"
        assert S < 2.0, f"Weight sum S={S} should be reasonable (< 2.0)"

    def test_all_max_components_bounded(self):
        """All components at 100 → omega ≤ 100."""
        entry = MemoryEntry(
            id="max", content="Maximum risk",
            type="tool_state", timestamp_age_days=999,
            source_trust=0.01, source_conflict=0.99,
            downstream_count=100, r_belief=0.01,
        )
        result = compute([entry], "destructive", "medical")
        assert result.omega_mem_final <= 100

    def test_all_min_components_bounded(self):
        """All components at 0 → omega ≥ 0."""
        entry = MemoryEntry(
            id="min", content="Minimum risk",
            type="identity", timestamp_age_days=0.001,
            source_trust=0.999, source_conflict=0.001,
            downstream_count=0, r_belief=0.999,
        )
        result = compute([entry], "informational", "general")
        assert result.omega_mem_final >= 0


# ---------------------------------------------------------------------------
# #615: Healing Termination (empirical, small sample)
# ---------------------------------------------------------------------------

class TestHealingTermination:
    def test_refetch_reduces_omega(self):
        """REFETCH (set age=0) should reduce omega."""
        entry = MemoryEntry(
            id="ht1", content="Stale data", type="tool_state",
            timestamp_age_days=100, source_trust=0.7,
            source_conflict=0.2, downstream_count=5, r_belief=0.8,
        )
        omega_before = compute([entry], "reversible", "general").omega_mem_final
        healed = MemoryEntry(
            id="ht1", content="Stale data", type="tool_state",
            timestamp_age_days=0.1, source_trust=0.7,
            source_conflict=0.2, downstream_count=5, r_belief=0.8,
        )
        omega_after = compute([healed], "reversible", "general").omega_mem_final
        assert omega_after <= omega_before

    def test_verify_reduces_omega(self):
        """VERIFY (set trust=0.99) should reduce omega."""
        entry = MemoryEntry(
            id="ht2", content="Untrusted data", type="semantic",
            timestamp_age_days=10, source_trust=0.3,
            source_conflict=0.6, downstream_count=5, r_belief=0.5,
        )
        omega_before = compute([entry], "reversible", "general").omega_mem_final
        healed = MemoryEntry(
            id="ht2", content="Untrusted data", type="semantic",
            timestamp_age_days=10, source_trust=0.99,
            source_conflict=0.01, downstream_count=5, r_belief=0.5,
        )
        omega_after = compute([healed], "reversible", "general").omega_mem_final
        assert omega_after <= omega_before


# ---------------------------------------------------------------------------
# #618: A2 Axiom
# ---------------------------------------------------------------------------

class TestA2Axiom:
    def test_identical_input_identical_output(self):
        """Same input → same omega (10 decimal places)."""
        entry = MemoryEntry(
            id="a2", content="Deterministic test", type="semantic",
            timestamp_age_days=42, source_trust=0.73,
            source_conflict=0.18, downstream_count=7, r_belief=0.61,
        )
        r1 = compute([entry], "irreversible", "fintech")
        r2 = compute([entry], "irreversible", "fintech")
        assert r1.omega_mem_final == r2.omega_mem_final

    def test_100_cases_deterministic(self):
        """100 random cases: two runs produce identical omega."""
        for seed in range(100):
            rng = random.Random(seed)
            entry = MemoryEntry(
                id=f"det_{seed}", content=f"Content {seed}",
                type="semantic", timestamp_age_days=rng.uniform(0, 200),
                source_trust=rng.uniform(0.1, 0.9),
                source_conflict=rng.uniform(0.05, 0.5),
                downstream_count=rng.randint(1, 20),
                r_belief=rng.uniform(0.3, 0.9),
            )
            r1 = compute([entry], "reversible", "general")
            r2 = compute([entry], "reversible", "general")
            assert r1.omega_mem_final == r2.omega_mem_final, f"seed={seed} non-deterministic"
