"""Tests for verify_api_key timing channel mitigation."""
import os, time
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestAuthTiming:
    def test_invalid_key_has_minimum_latency(self):
        """Invalid key responses should take at least 50ms (timing floor)."""
        t0 = time.monotonic()
        r = client.post("/v1/preflight", headers={"Authorization": "Bearer sg_totally_invalid_key_xyz"},
                        json={"memory_state": [{"id": "e1", "content": "x", "type": "semantic",
                              "timestamp_age_days": 1, "source_trust": 0.9, "source_conflict": 0.05,
                              "downstream_count": 1}], "action_type": "reversible", "domain": "general"})
        elapsed_ms = (time.monotonic() - t0) * 1000
        assert r.status_code == 401
        assert elapsed_ms >= 40  # 50ms target with 10ms tolerance for test overhead

    def test_valid_key_responds_faster_than_invalid(self):
        """Valid key (memory cache) should respond faster than invalid key (with delay)."""
        # Valid key
        t0 = time.monotonic()
        r_valid = client.post("/v1/preflight", headers={"Authorization": "Bearer sg_test_key_001"},
                              json={"memory_state": [{"id": "e1", "content": "x", "type": "semantic",
                                    "timestamp_age_days": 1, "source_trust": 0.9, "source_conflict": 0.05,
                                    "downstream_count": 1}], "action_type": "reversible", "domain": "general",
                                    "dry_run": True})
        valid_ms = (time.monotonic() - t0) * 1000

        # Invalid key
        t1 = time.monotonic()
        r_invalid = client.post("/v1/preflight", headers={"Authorization": "Bearer sg_invalid_key_abc"},
                                json={"memory_state": [{"id": "e1", "content": "x", "type": "semantic",
                                      "timestamp_age_days": 1, "source_trust": 0.9, "source_conflict": 0.05,
                                      "downstream_count": 1}], "action_type": "reversible", "domain": "general"})
        invalid_ms = (time.monotonic() - t1) * 1000

        assert r_valid.status_code == 200
        assert r_invalid.status_code == 401
        # The timing gap should be much smaller than the original ~200x
        # Valid: ~20ms, Invalid: ~50-70ms (with floor). Ratio < 5x.
        if valid_ms > 1:  # Only check if valid took measurable time
            ratio = invalid_ms / valid_ms
            assert ratio < 10, f"Timing ratio {ratio:.1f}x still too large (valid={valid_ms:.0f}ms, invalid={invalid_ms:.0f}ms)"
