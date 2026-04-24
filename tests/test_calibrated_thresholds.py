"""Tests for #771 calibrated_thresholds field in preflight response."""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def _entry(**overrides):
    defaults = {
        "id": "ct_001",
        "content": "Test memory for calibrated thresholds",
        "type": "preference",
        "timestamp_age_days": 1,
        "source_trust": 0.95,
        "source_conflict": 0.05,
        "downstream_count": 1,
        "r_belief": 0.5,
        "healing_counter": 0,
    }
    defaults.update(overrides)
    return defaults


class TestCalibratedThresholds:
    def test_field_present(self):
        """calibrated_thresholds must appear in preflight response (None or dict)."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational",
            "domain": "general",
        })
        assert r.status_code == 200
        data = r.json()
        assert "calibrated_thresholds" in data

    def test_null_without_history(self):
        """Without 20+ history entries, calibrated_thresholds should be null."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational",
            "domain": "general",
        })
        data = r.json()
        assert data["calibrated_thresholds"] is None

    def test_field_type(self):
        """calibrated_thresholds must be None or a dict with expected keys."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational",
            "domain": "general",
        })
        ct = r.json()["calibrated_thresholds"]
        if ct is not None:
            assert "r_warn" in ct
            assert "r_block" in ct
            assert "samples" in ct
            assert "confidence" in ct
