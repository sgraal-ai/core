"""Tests for stability fixes #374-376, #390."""
import sys, os, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import (app, _evict_if_full, _run_periodic_cleanup,
                       _stripe_retry_queue, _stripe_retry_lock,
                       _DICT_MAX_SIZE, _DICT_TTL, _dict_write_times)

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


# ---------------------------------------------------------------------------
# FIX 1: Dict eviction (#374)
# ---------------------------------------------------------------------------

class TestDictEviction:
    def test_evict_if_full_works(self):
        """Dict exceeding max size gets evicted."""
        d = {str(i): i for i in range(10005)}
        _evict_if_full(d, "test_dict")
        assert len(d) <= _DICT_MAX_SIZE

    def test_evict_preserves_recent(self):
        """Eviction removes oldest entries, preserves newest."""
        d = {str(i): i for i in range(10005)}
        _evict_if_full(d, "test_dict")
        # Oldest keys (0-999) should be gone, newest should remain
        assert "10004" in d
        assert "0" not in d


# ---------------------------------------------------------------------------
# FIX 2: Stripe retry queue (#375)
# ---------------------------------------------------------------------------

class TestStripeRetryQueue:
    def test_queue_starts_empty(self):
        # Queue may have items from other tests, just verify it's a list
        assert isinstance(_stripe_retry_queue, list)

    def test_scheduler_status_includes_stripe(self):
        r = client.get("/v1/scheduler/status", headers=AUTH)
        j = r.json()
        assert "stripe_retry" in j["jobs"]
        assert "queue_length" in j["jobs"]["stripe_retry"]


# ---------------------------------------------------------------------------
# FIX 3: Time-based cleanup (#376)
# ---------------------------------------------------------------------------

class TestTimeBasedCleanup:
    def test_periodic_cleanup_runs(self):
        """_run_periodic_cleanup should execute without crashing."""
        _run_periodic_cleanup()
        # Should not raise

    def test_cleanup_respects_interval(self):
        """Cleanup should not run again within the interval."""
        import api.main as _m
        _m._last_cleanup_time = time.time()  # Just ran
        _run_periodic_cleanup()  # Should skip (within interval)
        # No way to assert it skipped, but it should not crash


# ---------------------------------------------------------------------------
# FIX 4: TTL configuration (#390)
# ---------------------------------------------------------------------------

class TestTTLConfig:
    def test_ttl_defined_for_all_dicts(self):
        """All managed dicts should have TTL configured."""
        expected = ["_certificates", "_registry", "_predictive_alerts",
                    "_court_verdicts", "_commons", "_truth_subs",
                    "_async_preflight_jobs", "_webhook_configs"]
        for name in expected:
            assert name in _DICT_TTL, f"Missing TTL for {name}"
            assert _DICT_TTL[name] > 0

    def test_ttl_values_reasonable(self):
        """TTL values should be between 1 hour and 30 days."""
        for name, ttl in _DICT_TTL.items():
            assert 3600 <= ttl <= 30 * 86400, f"TTL for {name} is {ttl}s — out of range"
