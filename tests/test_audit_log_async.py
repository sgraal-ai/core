"""Tests for #3: async audit_log with timeout.

_audit_log() now runs the Supabase write in a thread pool with a 5-second
timeout. A slow or failing write must NOT block the preflight response.
"""
import os
import sys
import time
from unittest.mock import patch, MagicMock

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

_HEALTHY = [{
    "id": "m1", "content": "fresh", "type": "preference",
    "timestamp_age_days": 1, "source_trust": 0.95,
    "source_conflict": 0.05, "downstream_count": 1,
}]


class TestAuditLogAsync:
    def test_slow_audit_does_not_block_preflight(self):
        """If the Supabase write takes longer than the timeout, the preflight
        response must still return promptly — the write continues in the
        background but does not delay the caller."""

        def _slow_insert(*args, **kwargs):
            """Simulate a 10-second Supabase outage."""
            time.sleep(10)
            return MagicMock()

        with patch("api.main._audit_log_sync", side_effect=_slow_insert):
            t0 = time.monotonic()
            r = client.post("/v1/preflight", headers=AUTH, json={
                "memory_state": _HEALTHY,
                "action_type": "reversible",
                "domain": "general",
            })
            elapsed = time.monotonic() - t0

        assert r.status_code == 200
        d = r.json()
        assert "omega_mem_final" in d
        # The preflight must return well before the 10-second simulated outage.
        # With a 5-second timeout, the call returns in ≤ ~6 seconds (5s wait +
        # some overhead). It must NOT wait the full 10 seconds.
        assert elapsed < 8.0, (
            f"Preflight took {elapsed:.1f}s — audit log timeout ({5.0}s) "
            f"should have prevented waiting for the full 10s simulated outage"
        )

    def test_audit_log_records_on_normal_operation(self):
        """When Supabase is responsive (or absent in test env), the preflight
        response must include all expected fields and complete normally.
        The audit_log write is fire-and-forget — its success or failure
        does not affect the response shape."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _HEALTHY,
            "action_type": "reversible",
            "domain": "general",
        })
        assert r.status_code == 200
        d = r.json()
        assert "omega_mem_final" in d
        assert "recommended_action" in d
        # The response shape is unchanged regardless of audit_log outcome.
        # In test env without Supabase, the write is a no-op (no client),
        # but the response must still be complete.
        assert "decision_trail" in d
        assert "scoring_warnings" in d
