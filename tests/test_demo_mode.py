"""Tests for #27: demo_mode flag on analytics/summary and #39/#44 config."""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


class TestDemoMode:
    def test_analytics_summary_includes_demo_mode(self):
        """GET /v1/analytics/summary must include demo_mode field."""
        r = client.get("/v1/analytics/summary", headers=AUTH)
        assert r.status_code == 200
        d = r.json()
        assert "demo_mode" in d
        assert isinstance(d["demo_mode"], bool)

    def test_demo_mode_true_when_no_calls(self):
        """In a fresh test environment with zero preflight calls via the
        metrics counter, demo_mode should be True."""
        r = client.get("/v1/analytics/summary", headers=AUTH)
        d = r.json()
        # In test env, _metrics.preflight_total may or may not be 0 depending
        # on whether other tests ran first (tests share the process).
        # But demo_mode MUST be present and be a bool.
        if d["total_calls"] == 0:
            assert d["demo_mode"] is True
        else:
            # If prior tests incremented the counter, demo_mode should be False
            assert d["demo_mode"] is False
