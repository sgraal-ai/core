"""Test #12: HMM fast path assert fires if N_STATES != 3.

The K=3 unrolled forward/backward loops in hmm.py index scalar variables
a00..a22 for exactly 3 states. If N_STATES is changed, these loops produce
silently wrong results. The assert added in this fix must crash loudly
instead of computing garbage.
"""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import scoring_engine.hmm as hmm_module

# 25 entries — well above the default min_observations=20
_HISTORY = [50, 55, 60, 65, 70, 75, 80, 75, 70, 65,
            60, 55, 50, 45, 40, 35, 30, 35, 40, 45,
            50, 55, 60, 65, 70]


class TestHMMNStatesGuard:
    def test_assert_fires_when_n_states_changed(self):
        """Monkeypatch N_STATES to 4; verify AssertionError propagates.

        The assert is in compute_hmm_regime() OUTSIDE the try/except in
        _compute_hmm_regime_cached, so it is never swallowed.
        """
        # Clear cache to prevent stale cached results from interfering
        hmm_module._clear_hmm_cache()
        original = hmm_module.N_STATES
        try:
            hmm_module.N_STATES = 4
            with pytest.raises(AssertionError, match="exactly 3 states"):
                hmm_module.compute_hmm_regime(
                    score_history=_HISTORY,
                    current_score=50.0,
                )
        finally:
            hmm_module.N_STATES = original
            hmm_module._clear_hmm_cache()

    def test_assert_does_not_fire_with_default_n_states(self):
        """Normal operation: N_STATES=3 must NOT raise, and must return a result."""
        hmm_module._clear_hmm_cache()
        assert hmm_module.N_STATES == 3
        result = hmm_module.compute_hmm_regime(
            score_history=_HISTORY,
            current_score=50.0,
        )
        assert result is not None, (
            f"compute_hmm_regime returned None with {len(_HISTORY)} observations "
            f"(min_observations=20). Check that _initial_params and _baum_welch_np "
            f"succeed with this input."
        )
        assert result.current_state in ("STABLE", "DEGRADING", "CRITICAL")
