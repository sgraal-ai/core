"""Tests for #826 Stripe retry queue with exponential backoff and dead letter."""
import os
import time

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from fastapi.testclient import TestClient
from api.main import (app, _stripe_retry_queue, _stripe_retry_lock,
                      _STRIPE_MAX_RETRIES, _STRIPE_BACKOFF_SECONDS,
                      _stripe_move_to_dead_letter)
from api.redis_state import redis_available

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


class TestStripeRetry:
    def test_enqueue_dequeue_roundtrip(self):
        """Items added to queue survive and are retrievable."""
        item = {"customer_id": "cus_test_rt", "retry_count": 0,
                "failed_at": time.time(), "next_retry_at": 0}
        with _stripe_retry_lock:
            _stripe_retry_queue.append(item)
        assert any(i["customer_id"] == "cus_test_rt" for i in _stripe_retry_queue)
        # Cleanup
        with _stripe_retry_lock:
            _stripe_retry_queue[:] = [i for i in _stripe_retry_queue if i["customer_id"] != "cus_test_rt"]

    def test_max_retries_and_backoff_config(self):
        """Max retries is 5 and backoff schedule matches spec."""
        assert _STRIPE_MAX_RETRIES == 5
        assert len(_STRIPE_BACKOFF_SECONDS) == 5
        assert _STRIPE_BACKOFF_SECONDS == [10, 30, 90, 270, 810]

    def test_dead_letter_move(self):
        """After max retries, item moves to dead letter queue."""
        if not redis_available():
            import pytest
            pytest.skip("Redis not available")
        item = {"customer_id": "cus_dead_test", "retry_count": 5,
                "failed_at": time.time()}
        _stripe_move_to_dead_letter(item)
        from api.redis_state import redis_get
        dl = redis_get("sgraal:stripe_dead_letter")
        assert isinstance(dl, list)
        assert any(i.get("customer_id") == "cus_dead_test" for i in dl)

    def test_dead_letter_endpoint(self):
        """Dead letter endpoint returns expected structure."""
        r = client.get("/v1/admin/stripe-dead-letter", headers=AUTH)
        assert r.status_code == 200
        j = r.json()
        assert "items" in j
        assert "count" in j
        assert isinstance(j["items"], list)
