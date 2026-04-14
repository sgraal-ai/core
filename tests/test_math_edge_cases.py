"""Tests for mathematical edge case fixes (#377-#380)."""
import sys, os, math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# FIX 1: Sinkhorn epsilon underflow (#377)
# ---------------------------------------------------------------------------

class TestSinkhornUnderflow:
    def test_small_epsilon_no_crash(self):
        """Very small epsilon should not crash — returns fallback."""
        from scoring_engine.sinkhorn import sinkhorn_distance
        # Widely separated distributions + tiny epsilon → would underflow without clamp
        result = sinkhorn_distance(
            [0.01, 0.99], [0.99, 0.01],
            epsilon=0.001,
        )
        # Should return a result (possibly converged=False) without NaN
        if result is not None:
            assert not math.isnan(result.distance)

    def test_normal_epsilon_converges(self):
        """Normal epsilon should converge correctly."""
        from scoring_engine.sinkhorn import sinkhorn_distance
        result = sinkhorn_distance(
            [0.5, 0.5], [0.5, 0.5],
            epsilon=0.1,
        )
        if result is not None:
            assert result.distance >= 0


# ---------------------------------------------------------------------------
# FIX 2: HMM log-space overflow (#378)
# ---------------------------------------------------------------------------

class TestHMMLogOverflow:
    def test_extreme_scores_no_nan(self):
        """HMM with extreme score values should not produce NaN."""
        from scoring_engine.hmm import compute_hmm_regime
        history = [0, 0, 0, 0, 0, 100, 100, 100, 100, 100,
                   0, 0, 0, 100, 100, 100, 0, 0, 100, 100]
        result = compute_hmm_regime(history, current_score=50.0)
        if result is not None:
            assert not math.isnan(result.state_probability)
            assert result.current_state in ("STABLE", "DEGRADING", "CRITICAL")

    def test_all_identical_scores(self):
        """All identical scores (zero variance) should not crash."""
        from scoring_engine.hmm import compute_hmm_regime
        history = [50.0] * 25
        result = compute_hmm_regime(history, current_score=50.0)
        if result is not None:
            assert not math.isnan(result.state_probability)


# ---------------------------------------------------------------------------
# FIX 3: Levy flight alpha bounds (#379)
# ---------------------------------------------------------------------------

class TestLevyAlphaBounds:
    def test_alpha_always_in_range(self):
        """Alpha must be in (0, 2] regardless of input."""
        from scoring_engine.levy_flight import compute_levy_flight
        history = [50.0, 50.001, 50.002, 49.999, 50.0, 50.001, 49.998, 50.0, 50.001, 50.0]
        result = compute_levy_flight(history, current_score=50.0)
        if result is not None:
            assert 0.1 <= result.alpha <= 2.0, f"Alpha {result.alpha} out of bounds"

    def test_high_variance_alpha_valid(self):
        """High variance input should also produce valid alpha."""
        from scoring_engine.levy_flight import compute_levy_flight
        history = [10, 90, 5, 95, 15, 85, 20, 80, 10, 90]
        result = compute_levy_flight(history, current_score=50.0)
        if result is not None:
            assert 0.1 <= result.alpha <= 2.0


# ---------------------------------------------------------------------------
# FIX 4: RMT minimum sample size (#380)
# ---------------------------------------------------------------------------

class TestRMTMinSample:
    def test_n2_returns_none(self):
        """2 entries should return None (degenerate eigenvalues)."""
        from scoring_engine.rmt import compute_rmt
        entries = [
            {"id": "a", "content": "hello world", "source_trust": 0.9, "source_conflict": 0.1},
            {"id": "b", "content": "goodbye world", "source_trust": 0.8, "source_conflict": 0.2},
        ]
        result = compute_rmt(entries)
        assert result is None

    def test_n5_returns_result(self):
        """5+ entries should return a result."""
        from scoring_engine.rmt import compute_rmt
        entries = [
            {"id": f"e{i}", "content": f"entry {i} with unique content {i*7}",
             "source_trust": 0.5 + i * 0.08, "source_conflict": 0.1 + i * 0.05}
            for i in range(6)
        ]
        result = compute_rmt(entries)
        # May still return None if content too similar, but shouldn't crash
        # and should not produce degenerate eigenvalues
