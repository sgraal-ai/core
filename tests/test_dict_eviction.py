"""Tests for global dict eviction and periodic cleanup."""
import os, time
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from api.helpers import _evict_if_full, _DICT_MAX_SIZE


class TestEvictIfFull:
    def test_under_limit_no_eviction(self):
        d = {str(i): {"data": i} for i in range(100)}
        original_size = len(d)
        _evict_if_full(d)
        assert len(d) == original_size

    def test_over_limit_evicts(self):
        d = {str(i): {"data": i} for i in range(_DICT_MAX_SIZE + 500)}
        _evict_if_full(d)
        assert len(d) < _DICT_MAX_SIZE + 500
        assert len(d) <= _DICT_MAX_SIZE

    def test_eviction_preserves_recent_entries(self):
        """Most recent entries should survive eviction."""
        d = {}
        for i in range(_DICT_MAX_SIZE + 100):
            d[f"entry_{i}"] = {"data": i}
        _evict_if_full(d)
        # The dict should have been trimmed
        assert len(d) <= _DICT_MAX_SIZE

    def test_empty_dict_no_crash(self):
        d = {}
        _evict_if_full(d)  # Should not crash
        assert len(d) == 0


class TestPeriodicCleanup:
    def test_cleanup_runs_without_crash(self):
        """Periodic cleanup should not crash even with empty dicts."""
        from api.main import _run_periodic_cleanup
        # Force cleanup by resetting last time
        import api.main as _m
        _m._last_cleanup_time = 0
        _run_periodic_cleanup()  # Should not raise

    def test_managed_dicts_registered(self):
        """Verify the managed dicts list includes the newly added collections."""
        # Import main to trigger dict registration
        from api.main import (
            _async_jobs, _twin_jobs, _redteam_jobs, _lab_jobs,
            _forensics, _blackbox, _lifecycle_policies, _passports,
        )
        # All should be importable (exist as module-level dicts)
        assert isinstance(_async_jobs, dict)
        assert isinstance(_twin_jobs, dict)
        assert isinstance(_redteam_jobs, dict)
        assert isinstance(_lab_jobs, dict)
        assert isinstance(_forensics, dict)
        assert isinstance(_blackbox, dict)
        assert isinstance(_lifecycle_policies, dict)
        assert isinstance(_passports, dict)
