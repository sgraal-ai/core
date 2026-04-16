"""Tests for HMM optimization.

Verifies:
  1. Identity preservation — output for a fixed input matches a snapshot.
  2. Determinism — same input produces identical output on repeated calls.
  3. Cache hit benefit — second call is >=2x faster than first (cold) call.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

os.environ.setdefault("SGRAAL_SKIP_DNS_CHECK", "1")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scoring_engine.hmm import (  # noqa: E402
    HMMRegimeResult,
    _clear_hmm_cache,
    compute_hmm_regime,
)


# Fixed input — a monotonic ramp that exercises the CRITICAL regime.
# This is the canonical reference; the expected output below is a snapshot
# captured from the optimized implementation. Any regression that silently
# changes Baum-Welch convergence, parameter initialization, Viterbi tie-break,
# or rounding will trip this test.
_REF_HISTORY = [30.0 + i * 0.5 for i in range(21)]
_REF_CURRENT = 40.0

# Snapshot of the current optimized output — captured from compute_hmm_regime.
_REF_EXPECTED = {
    "current_state": "CRITICAL",
    "state_probability": 1.0,
    "regime_duration": 8,
    "transition_probs": {
        "to_stable": 0.0,
        "to_degrading": 0.0,
        "to_critical": 1.0,
    },
}


class TestHMMIdentityPreservation:
    """Output must match a fixed snapshot — guards against silent semantic drift."""

    def test_reference_matches_snapshot(self):
        _clear_hmm_cache()
        result = compute_hmm_regime(_REF_HISTORY, _REF_CURRENT)
        assert isinstance(result, HMMRegimeResult)
        assert result.current_state == _REF_EXPECTED["current_state"]
        assert abs(result.state_probability - _REF_EXPECTED["state_probability"]) < 1e-6
        assert result.regime_duration == _REF_EXPECTED["regime_duration"]
        for key, want in _REF_EXPECTED["transition_probs"].items():
            got = result.transition_probs[key]
            assert abs(got - want) < 1e-6, f"{key}: got {got}, want {want}"

    def test_trimodal_snapshot(self):
        """Second independent snapshot covering a different regime path."""
        _clear_hmm_cache()
        history = [20, 22, 50, 55, 80, 85, 20, 22, 50, 55,
                   80, 85, 20, 22, 50, 55, 80, 85, 20, 22]
        result = compute_hmm_regime(history, 50.0)
        assert result is not None
        assert result.current_state == "DEGRADING"
        assert abs(result.state_probability - 1.0) < 1e-6
        tp = result.transition_probs
        # Transition probs should sum to ~1.0 and match snapshot.
        assert abs(tp["to_stable"] + tp["to_degrading"] + tp["to_critical"] - 1.0) < 1e-3
        assert abs(tp["to_stable"] - 0.0) < 1e-3
        assert abs(tp["to_degrading"] - 0.5) < 1e-3
        assert abs(tp["to_critical"] - 0.5) < 1e-3


class TestHMMDeterminism:
    """Same input → identical output across repeated calls (even after cache clears)."""

    def test_repeated_calls_identical(self):
        history = [25.0 + i * 0.3 for i in range(24)]
        current = 32.0

        _clear_hmm_cache()
        results = []
        for _ in range(5):
            # Clear cache between calls so we exercise the full compute path, not the cache.
            _clear_hmm_cache()
            results.append(compute_hmm_regime(history, current))

        first = results[0]
        assert first is not None
        for r in results[1:]:
            assert r is not None
            assert r.current_state == first.current_state
            assert r.state_probability == first.state_probability  # bit-identical
            assert r.regime_duration == first.regime_duration
            assert r.transition_probs == first.transition_probs

    def test_cache_returns_same_object_or_equal_values(self):
        """With the LRU cache in place, repeated identical calls return the cached result."""
        _clear_hmm_cache()
        history = [15.0 + (i % 3) * 0.5 for i in range(25)]
        r1 = compute_hmm_regime(history, 15.0)
        r2 = compute_hmm_regime(history, 15.0)
        r3 = compute_hmm_regime(history, 15.0)
        assert r1 is not None and r2 is not None and r3 is not None
        assert r1.current_state == r2.current_state == r3.current_state
        assert r1.state_probability == r2.state_probability == r3.state_probability
        assert r1.regime_duration == r2.regime_duration == r3.regime_duration
        assert r1.transition_probs == r2.transition_probs == r3.transition_probs


class TestHMMCacheSpeedup:
    """LRU cache: second call with identical input must be substantially faster than the first."""

    def test_cache_hit_is_faster(self):
        history = [30.0 + i * 0.5 for i in range(21)]
        current = 40.0

        _clear_hmm_cache()

        # Cold call — fully computes.
        t0 = time.perf_counter()
        cold = compute_hmm_regime(history, current)
        cold_ns = time.perf_counter() - t0
        assert cold is not None

        # Warm calls — should hit the LRU cache.
        warm_times = []
        for _ in range(10):
            t0 = time.perf_counter()
            warm = compute_hmm_regime(history, current)
            warm_times.append(time.perf_counter() - t0)
            assert warm is cold  # cache returns the exact same object

        # Use median warm time to reduce flakiness from GC/scheduler noise.
        warm_times.sort()
        warm_ns = warm_times[len(warm_times) // 2]

        # Cache lookup should be at least 2x faster than full compute.
        # In practice it's 1000x+, so 2x is a very loose floor.
        assert cold_ns > warm_ns * 2, (
            f"Expected warm ({warm_ns*1e6:.1f}us) < cold ({cold_ns*1e6:.1f}us)/2"
        )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
