"""Tests for weight normalization proof: omega ∈ [0, 100]."""
import os, random
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from scoring_engine.omega_mem import WEIGHTS, compute, MemoryEntry


class TestWeightNormalization:
    def test_weights_sum_positive(self):
        assert sum(abs(w) for w in WEIGHTS.values()) > 0

    def test_omega_bounded_max_risk(self):
        e = MemoryEntry(id="max", content="x", type="semantic",
            timestamp_age_days=1000, source_trust=0.0, source_conflict=1.0, downstream_count=100)
        r = compute([e])
        assert 0 <= r.omega_mem_final <= 100

    def test_omega_bounded_min_risk(self):
        e = MemoryEntry(id="min", content="x", type="semantic",
            timestamp_age_days=0, source_trust=1.0, source_conflict=0.0, downstream_count=0)
        r = compute([e])
        assert 0 <= r.omega_mem_final <= 100

    def test_random_entries_always_bounded(self):
        for _ in range(20):
            e = MemoryEntry(id="rnd", content="test", type="semantic",
                timestamp_age_days=random.uniform(0, 500),
                source_trust=random.uniform(0, 1),
                source_conflict=random.uniform(0, 1),
                downstream_count=random.randint(0, 50))
            r = compute([e])
            assert 0 <= r.omega_mem_final <= 100
