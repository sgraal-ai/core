"""Tests for heal_roi, knowledge_age_days, and fleet_health_distance preflight fields."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def _entry(**overrides):
    defaults = {
        "id": "hr_001", "content": "Test memory", "type": "preference",
        "timestamp_age_days": 10, "source_trust": 0.9, "source_conflict": 0.1,
        "downstream_count": 3,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# heal_roi
# ---------------------------------------------------------------------------

class TestHealROI:
    def test_repair_plan_entries_have_heal_roi(self):
        """Each repair plan entry should have a heal_roi field."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _entry(id="roi_1", timestamp_age_days=200, source_trust=0.3, source_conflict=0.7, downstream_count=20),
            ],
            "action_type": "irreversible", "domain": "fintech",
        })
        assert r.status_code == 200
        rp = r.json().get("repair_plan", [])
        for item in rp:
            assert "heal_roi" in item
            assert isinstance(item["heal_roi"], (int, float))

    def test_top_roi_entry_id_present(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        assert "top_roi_entry_id" in r.json()

    def test_top_roi_null_when_no_repair(self):
        """If no repair actions needed, top_roi_entry_id is null."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry(timestamp_age_days=0.1, source_trust=0.99, source_conflict=0.01, downstream_count=1)],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        if not j.get("repair_plan"):
            assert j["top_roi_entry_id"] is None

    def test_repair_plan_sorted_by_roi_descending(self):
        """Repair plan should be sorted by heal_roi descending."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _entry(id="roi_a", timestamp_age_days=300, source_trust=0.2, source_conflict=0.8, downstream_count=30),
                _entry(id="roi_b", timestamp_age_days=100, source_trust=0.5, source_conflict=0.4, downstream_count=10),
            ],
            "action_type": "destructive", "domain": "medical",
        })
        rp = r.json().get("repair_plan", [])
        if len(rp) >= 2:
            rois = [item["heal_roi"] for item in rp]
            assert rois == sorted(rois, reverse=True)


# ---------------------------------------------------------------------------
# knowledge_age_days
# ---------------------------------------------------------------------------

class TestKnowledgeAge:
    def test_field_present(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        assert "knowledge_age_days" in j
        assert "knowledge_age_std_days" in j

    def test_single_entry_std_zero(self):
        """Single entry → std = 0.0."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry(timestamp_age_days=5)],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        assert j["knowledge_age_std_days"] == 0.0

    def test_mean_reflects_ages(self):
        """Mean should reflect the ages of the entries."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _entry(id="ka_1", timestamp_age_days=10, source_trust=0.9),
                _entry(id="ka_2", timestamp_age_days=20, source_trust=0.9),
            ],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        # With equal trust, mean should be ~15
        assert 10 <= j["knowledge_age_days"] <= 20

    def test_trust_weighting(self):
        """Higher-trust entries should weight more heavily."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _entry(id="tw_1", timestamp_age_days=10, source_trust=0.99),
                _entry(id="tw_2", timestamp_age_days=100, source_trust=0.01),
            ],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        # High-trust entry is 10 days, low-trust is 100 days → mean should be closer to 10
        assert j["knowledge_age_days"] < 50


# ---------------------------------------------------------------------------
# fleet_health_distance
# ---------------------------------------------------------------------------

class TestFleetHealthDistance:
    def test_fields_present(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        assert "fleet_health_distance" in j
        assert "fleet_health_distance_available" in j

    def test_null_without_fleet_data(self):
        """Without sufficient fleet history, returns null."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        # Test keys skip Redis, so fleet data unavailable
        assert j["fleet_health_distance"] is None
        assert j["fleet_health_distance_available"] is False

    def test_available_is_boolean(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        assert isinstance(r.json()["fleet_health_distance_available"], bool)
