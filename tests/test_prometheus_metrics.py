"""Tests for #802 Prometheus metrics endpoint."""
import os
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from fastapi.testclient import TestClient
from api.main import app, _metrics

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


class TestPrometheusMetrics:
    def test_metrics_format_valid(self):
        """Metrics endpoint returns valid Prometheus text format."""
        r = client.get("/metrics")
        assert r.status_code == 200
        text = r.text
        assert "sgraal_preflight_total" in text
        assert "sgraal_decision_total" in text
        assert "sgraal_preflight_latency_seconds_bucket" in text
        assert "sgraal_omega_bucket" in text
        assert "sgraal_active_tenants" in text
        assert "sgraal_redis_health" in text
        # Verify TYPE lines
        assert "# TYPE sgraal_preflight_total counter" in text
        assert "# TYPE sgraal_preflight_latency_seconds histogram" in text

    def test_counter_increments(self):
        """Preflight counter increments after a call."""
        before = _metrics.preflight_total
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{"id": "e1", "content": "test", "type": "semantic",
                              "timestamp_age_days": 1, "source_trust": 0.9,
                              "source_conflict": 0.05, "downstream_count": 1}],
            "domain": "general", "action_type": "informational",
        })
        assert r.status_code == 200
        assert _metrics.preflight_total > before

    def test_metrics_auth_when_token_set(self):
        """When SGRAAL_METRICS_TOKEN is set, auth is required."""
        import api.main as m
        old_token = m._METRICS_TOKEN
        m._METRICS_TOKEN = "test_secret_token"
        try:
            # Without token → 401
            r = client.get("/metrics")
            assert r.status_code == 401
            # With token → 200
            r = client.get("/metrics", headers={"Authorization": "Bearer test_secret_token"})
            assert r.status_code == 200
        finally:
            m._METRICS_TOKEN = old_token
