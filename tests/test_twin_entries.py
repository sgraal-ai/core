"""Tests for #772 twin_entries field in preflight response."""
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
        "id": "tw_001",
        "content": "Unique memory content for twin detection",
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


class TestTwinEntries:
    def test_no_twins_clean(self):
        """Distinct entries should produce flag=clean."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _entry(id="tw_a", content="The user prefers dark mode for the IDE"),
                _entry(id="tw_b", content="Deploy target is staging environment on AWS"),
            ],
            "action_type": "informational",
            "domain": "general",
        })
        assert r.status_code == 200
        tw = r.json()["twin_entries"]
        assert tw["flag"] == "clean"
        assert tw["count"] == 0

    def test_obvious_twins_detected(self):
        """Nearly identical entries should be detected as twins."""
        identical = "The quick brown fox jumps over the lazy dog near the river bank"
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _entry(id="tw_x", content=identical),
                _entry(id="tw_y", content=identical),
                _entry(id="tw_z", content="Completely different memory about database migrations"),
            ],
            "action_type": "informational",
            "domain": "general",
        })
        assert r.status_code == 200
        tw = r.json()["twin_entries"]
        assert tw["count"] >= 1
        assert len(tw["pairs"]) >= 1

    def test_single_entry_edge_case(self):
        """Single entry cannot have twins."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational",
            "domain": "general",
        })
        tw = r.json()["twin_entries"]
        assert tw["count"] == 0
        assert tw["flag"] == "clean"
