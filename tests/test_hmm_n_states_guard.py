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


class TestHMMNStatesGuard:
    def test_assert_fires_when_n_states_changed(self):
        """Monkeypatch N_STATES to 4; verify the fast path raises AssertionError."""
        original = hmm_module.N_STATES
        try:
            hmm_module.N_STATES = 4
            with pytest.raises(AssertionError, match="exactly 3 states"):
                hmm_module.compute_hmm_regime(
                    score_history=[50, 55, 60, 65, 70, 75, 80, 75, 70, 65,
                                   60, 55, 50, 45, 40, 35, 30, 35, 40, 45],
                    current_score=50.0,
                )
        finally:
            hmm_module.N_STATES = original

    def test_assert_does_not_fire_with_default_n_states(self):
        """Normal operation: N_STATES=3 must NOT raise."""
        assert hmm_module.N_STATES == 3
        result = hmm_module.compute_hmm_regime(
            score_history=[50, 55, 60, 65, 70, 75, 80, 75, 70, 65,
                           60, 55, 50, 45, 40, 35, 30, 35, 40, 45],
            current_score=50.0,
        )
        assert result is not None
        assert result.current_state in ("STABLE", "DEGRADING", "CRITICAL")
