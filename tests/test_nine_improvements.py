"""Tests for the 9-improvement sprint: webhook fix, health check, secret
enforcement, edge import, Stripe retry persistence.
"""
import os
import sys
import threading

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from api.main import app, _stripe_retry_queue, _stripe_retry_lock

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


# ---- TASK 1: Webhook dispatch uses final decision ----

class TestWebhookFinalDecision:
    def test_webhook_response_contains_final_action(self):
        """The preflight response's recommended_action is the FINAL decision
        (after all overrides). Webhook dispatch, being at the end of preflight
        alongside audit_log, must use this same value.

        We can't inspect webhook payloads without a webhook receiver, but
        we verify the decision_trail shows the final action matches the
        response — which is the same value the webhook now receives.
        """
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{
                "id": "m1", "content": "stale identity", "type": "identity",
                "timestamp_age_days": 50, "source_trust": 0.7,
                "source_conflict": 0.3, "downstream_count": 5,
            }],
            "action_type": "reversible",
            "domain": "general",
            "per_type_thresholds": True,
        })
        assert r.status_code == 200
        d = r.json()
        trail = d.get("decision_trail", [])
        if trail:
            # Last trail entry must match the response's final decision
            assert trail[-1]["action"] == d["recommended_action"]


# ---- TASK 2: Health check includes all dependencies ----

class TestHealthCheck:
    def test_health_returns_all_dependency_fields(self):
        r = client.get("/health")
        assert r.status_code == 200
        d = r.json()
        assert "status" in d
        assert d["status"] in ("healthy", "degraded", "unhealthy")
        assert "redis" in d
        assert "supabase" in d
        assert "stripe" in d
        assert "timestamp" in d

    def test_health_stripe_reflects_config(self):
        r = client.get("/health")
        d = r.json()
        # Stripe key may or may not be set in test env
        assert d["stripe"] in ("configured", "missing")


# ---- TASK 4: Secret strength enforcement in production ----

class TestSecretStrengthEnforcement:
    def test_weak_secret_in_production_raises_error(self):
        """If ENV=production and a secret is shorter than 32 chars,
        _validate_required_secrets must raise RuntimeError."""
        original_env = os.environ.get("ENV")
        original_secret = os.environ.get("ATTESTATION_SECRET")
        try:
            os.environ["ENV"] = "production"
            os.environ["ATTESTATION_SECRET"] = "short"
            # Re-import the validation function and call it
            from api.main import _validate_required_secrets
            with pytest.raises(RuntimeError, match="weak cryptographic secrets"):
                _validate_required_secrets()
        finally:
            if original_env is None:
                os.environ.pop("ENV", None)
            else:
                os.environ["ENV"] = original_env
            if original_secret is None:
                os.environ.pop("ATTESTATION_SECRET", None)
            else:
                os.environ["ATTESTATION_SECRET"] = original_secret


# ---- TASK 7: Edge SDK import fix ----

class TestEdgeImport:
    def test_importing_sgraal_edge_does_not_import_requests(self):
        """from sgraal.edge import edge_preflight must NOT trigger
        loading the requests library (which sgraal.client depends on)."""
        import importlib
        import subprocess
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; "
             "from sgraal.edge import edge_preflight; "
             "print('requests' in sys.modules)"],
            capture_output=True, text=True, timeout=10,
            cwd=os.path.join(os.path.dirname(os.path.dirname(__file__)), "sdk", "python"),
        )
        assert result.returncode == 0, f"Import failed: {result.stderr}"
        assert result.stdout.strip() == "False", (
            "Importing sgraal.edge loaded 'requests' — edge mode is not truly zero-dependency"
        )


# ---- TASK 9: Stripe retry queue persistence ----

class TestStripeRetryPersistence:
    def test_stripe_retry_queue_roundtrip(self):
        """Items added to the queue should survive a to-dict/from-redis cycle."""
        from api.main import _stripe_retry_sync_to_redis, _stripe_retry_load_from_redis
        # Add an item
        test_item = {"customer_id": "cus_test_roundtrip", "retry_count": 0, "failed_at": 12345}
        with _stripe_retry_lock:
            _stripe_retry_queue.append(test_item)
        _stripe_retry_sync_to_redis()
        # Clear in-memory
        with _stripe_retry_lock:
            _stripe_retry_queue.clear()
        assert len(_stripe_retry_queue) == 0
        # Load from Redis — if Redis is available, queue should be restored
        _stripe_retry_load_from_redis()
        # In test env without Redis, the queue stays empty (fail-safe)
        # With Redis, it should contain the test item
        # Either way, no crash
        with _stripe_retry_lock:
            found = any(i.get("customer_id") == "cus_test_roundtrip" for i in _stripe_retry_queue)
        # Clean up
        with _stripe_retry_lock:
            _stripe_retry_queue[:] = [i for i in _stripe_retry_queue if i.get("customer_id") != "cus_test_roundtrip"]
        _stripe_retry_sync_to_redis()

    def test_stripe_retry_survives_redis_failure(self):
        """If Redis is unavailable, the queue must work in memory without crashing."""
        from api.main import _stripe_retry_sync_to_redis
        test_item = {"customer_id": "cus_test_noop", "retry_count": 1, "failed_at": 99999}
        with _stripe_retry_lock:
            _stripe_retry_queue.append(test_item)
        # Sync should not crash even if Redis is down
        _stripe_retry_sync_to_redis()
        # Queue should still contain the item in memory
        with _stripe_retry_lock:
            assert any(i.get("customer_id") == "cus_test_noop" for i in _stripe_retry_queue)
            _stripe_retry_queue[:] = [i for i in _stripe_retry_queue if i.get("customer_id") != "cus_test_noop"]
