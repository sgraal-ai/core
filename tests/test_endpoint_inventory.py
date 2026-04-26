"""Tests for #834 endpoint inventory tracking."""
import os
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from fastapi.testclient import TestClient
import api.main as m
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


class TestEndpointInventory:
    def test_admin_endpoint_requires_token(self):
        """Endpoint inventory returns 404 when SGRAAL_ADMIN_TOKEN is not set."""
        old = m._ADMIN_TOKEN
        m._ADMIN_TOKEN = ""
        try:
            r = client.get("/v1/admin/endpoint-inventory")
            assert r.status_code == 404
        finally:
            m._ADMIN_TOKEN = old

    def test_admin_endpoint_returns_inventory(self):
        """With admin token, returns endpoint list with correct structure."""
        old = m._ADMIN_TOKEN
        m._ADMIN_TOKEN = "test_admin_secret"
        try:
            r = client.get("/v1/admin/endpoint-inventory",
                           headers={"Authorization": "Bearer test_admin_secret"})
            assert r.status_code == 200
            j = r.json()
            assert "endpoints" in j
            assert "total" in j
            assert j["total"] > 0
            # Every entry has expected fields
            for ep in j["endpoints"][:5]:
                assert "path" in ep
                assert "status" in ep
                assert ep["status"] in ("active", "candidate_for_deprecation", "likely_dead", "never_called")
        finally:
            m._ADMIN_TOKEN = old
