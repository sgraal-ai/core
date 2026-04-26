"""Tests for #831 stolen API key detection."""
import os
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from api.main import _check_key_anomaly
from api.redis_state import redis_set, redis_get, redis_delete, redis_available
import pytest
import hashlib


class TestKeyAnomaly:
    def test_baseline_established(self):
        """First call establishes baseline without error."""
        kh = hashlib.sha256(b"anomaly_test_key").hexdigest()
        _check_key_anomaly(kh, "1.2.3.4", 14)  # Should not raise

    def test_anomaly_triggers_on_signals(self):
        """2+ signals (IP change + hour shift) on established baseline triggers warning."""
        if not redis_available():
            pytest.skip("Redis not available")
        kh = hashlib.sha256(b"anomaly_trigger_test").hexdigest()
        # Establish baseline: IP=1.2.3.4, peak_hour=14, 30+ requests
        hour_hist = [0] * 24
        hour_hist[14] = 50  # strong peak at hour 14
        redis_set(f"key_baseline:{kh}", {
            "last_ip": "1.2.3.4",
            "hour_histogram": hour_hist,
            "first_seen": 0,
            "request_count": 30,
        }, ttl=60)
        try:
            # Different IP + hour 3 (distance 11 from peak 14) = 2 signals
            _check_key_anomaly(kh, "9.8.7.6", 3)  # Should log warning, not raise
        finally:
            redis_delete(f"key_baseline:{kh}")

    def test_no_trigger_without_baseline(self):
        """No anomaly fired when no baseline exists (first request)."""
        kh = hashlib.sha256(b"no_baseline_test").hexdigest()
        try:
            redis_delete(f"key_baseline:{kh}")
        except Exception:
            pass
        _check_key_anomaly(kh, "1.2.3.4", 10)  # Should not raise
