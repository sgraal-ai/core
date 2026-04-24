"""Tests for omega truncated norm properties."""
import os
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from scoring_engine.omega_mem import compute, MemoryEntry


def _entry(**kw):
    defaults = {"id": "t", "content": "x", "type": "semantic",
                "timestamp_age_days": 0, "source_trust": 0.5,
                "source_conflict": 0.1, "downstream_count": 1}
    defaults.update(kw)
    return MemoryEntry(**defaults)


class TestOmegaNormProperties:
    def test_p1_non_negativity(self):
        """P1: omega >= 0 for all valid inputs."""
        for age in [0, 10, 100, 500]:
            for trust in [0.0, 0.5, 1.0]:
                r = compute([_entry(timestamp_age_days=age, source_trust=trust)])
                assert r.omega_mem_final >= 0, f"P1 violated: age={age}, trust={trust}, omega={r.omega_mem_final}"

    def test_p2_definiteness(self):
        """P2: omega(zero-risk entry) should be near 0."""
        r = compute([_entry(timestamp_age_days=0, source_trust=1.0, source_conflict=0.0, downstream_count=0)])
        assert r.omega_mem_final < 5, f"P2: zero-risk entry produced omega={r.omega_mem_final}"

    def test_p3_subadditivity_pre_truncation(self):
        """P3: omega of combined entries <= sum of individual omegas (approximately, pre-truncation)."""
        e1 = _entry(id="a", timestamp_age_days=30, source_trust=0.7)
        e2 = _entry(id="b", timestamp_age_days=50, source_trust=0.4)
        r_combined = compute([e1, e2])
        r_1 = compute([e1])
        r_2 = compute([e2])
        # Pre-truncation: omega is averaged over entries, so combined should be between the two
        assert r_combined.omega_mem_final <= r_1.omega_mem_final + r_2.omega_mem_final + 1  # tolerance
