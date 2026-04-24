"""Tests for #770 sphere_position field in preflight response."""
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
        "id": "sp_001",
        "content": "Test memory for sphere",
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


class TestSpherePosition:
    def test_field_present(self):
        """sphere_position must appear in preflight response."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational",
            "domain": "general",
        })
        assert r.status_code == 200
        data = r.json()
        assert "sphere_position" in data
        sp = data["sphere_position"]
        assert "x" in sp and "y" in sp and "z" in sp and "zone" in sp

    def test_zone_safe_for_clean(self):
        """Clean fresh memory should land in safe zone."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational",
            "domain": "general",
        })
        data = r.json()
        sp = data["sphere_position"]
        # Fresh clean memory has low omega -> safe zone
        assert sp["zone"] in ("safe", "warn_boundary")

    def test_coordinates_in_range(self):
        """x, y, z must be in [0, 1]."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational",
            "domain": "general",
        })
        sp = r.json()["sphere_position"]
        assert 0 <= sp["x"] <= 1.0
        assert 0 <= sp["y"] <= 1.0
        assert 0 <= sp["z"] <= 1.0
