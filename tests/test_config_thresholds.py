"""Tests for Task 2: POST/GET /v1/config/thresholds."""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


class TestConfigThresholds:
    def test_set_and_get_thresholds_roundtrip(self):
        r = client.post(
            "/v1/config/thresholds",
            headers=AUTH,
            json={"domain": "fintech", "warn": 30, "ask_user": 50, "block": 75},
        )
        assert r.status_code == 200
        d = r.json()
        assert d["updated"] is True
        assert d["domain"] == "fintech"
        assert d["thresholds"]["warn"] == 30
        assert d["thresholds"]["ask_user"] == 50
        assert d["thresholds"]["block"] == 75

        # Roundtrip
        r2 = client.get("/v1/config/thresholds?domain=fintech", headers=AUTH)
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["domain"] == "fintech"
        assert d2["thresholds"]["warn"] == 30
        assert d2["thresholds"]["ask_user"] == 50
        assert d2["thresholds"]["block"] == 75
        # Note: source may be "custom" if Redis available, "default" if not (in-memory fallback may not persist)

    def test_invalid_ordering_rejected(self):
        r = client.post(
            "/v1/config/thresholds",
            headers=AUTH,
            json={"domain": "general", "warn": 50, "ask_user": 40, "block": 75},
        )
        assert r.status_code == 400
        assert "ordered" in r.json()["detail"].lower() or "warn" in r.json()["detail"].lower()

    def test_invalid_domain_rejected(self):
        r = client.post(
            "/v1/config/thresholds",
            headers=AUTH,
            json={"domain": "not_a_domain", "warn": 25, "ask_user": 45, "block": 70},
        )
        assert r.status_code == 400
        assert "domain" in r.json()["detail"].lower()

    def test_out_of_bounds_threshold_rejected(self):
        r = client.post(
            "/v1/config/thresholds",
            headers=AUTH,
            json={"domain": "general", "warn": -5, "ask_user": 45, "block": 70},
        )
        assert r.status_code == 400

        r = client.post(
            "/v1/config/thresholds",
            headers=AUTH,
            json={"domain": "general", "warn": 25, "ask_user": 45, "block": 150},
        )
        assert r.status_code == 400

    def test_get_defaults_when_no_custom_set(self):
        r = client.get("/v1/config/thresholds?domain=customer_support", headers=AUTH)
        assert r.status_code == 200
        d = r.json()
        assert d["domain"] == "customer_support"
        assert d["thresholds"]["warn"] == 25
        assert d["thresholds"]["ask_user"] == 45
        assert d["thresholds"]["block"] == 70

    def test_auth_required(self):
        r = client.post(
            "/v1/config/thresholds",
            json={"domain": "general", "warn": 25, "ask_user": 45, "block": 70},
        )
        assert r.status_code in (401, 403)
