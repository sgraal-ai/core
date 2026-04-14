"""Tests for counterfactual → heal connection (#252)."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def _entry(**overrides):
    defaults = {
        "id": "cf_001", "content": "Test memory", "type": "preference",
        "timestamp_age_days": 5, "source_trust": 0.9, "source_conflict": 0.1,
        "downstream_count": 2,
    }
    defaults.update(overrides)
    return defaults


class TestCounterfactualHeal:
    def test_fields_present(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry(), _entry(id="cf_002")],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        assert "counterfactual_heal_suggested" in j
        assert "counterfactual_top_entry_id" in j

    def test_false_for_clean_memory(self):
        """Clean, low-risk memory should not trigger counterfactual heal."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _entry(id="clean_1", source_trust=0.95, source_conflict=0.02, timestamp_age_days=1),
                _entry(id="clean_2", source_trust=0.9, source_conflict=0.05, timestamp_age_days=2),
            ],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        assert j["counterfactual_heal_suggested"] is False
        assert j["counterfactual_top_entry_id"] is None

    def test_suggested_for_one_bad_entry(self):
        """One very bad entry among clean ones should trigger counterfactual heal."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _entry(id="bad_1", timestamp_age_days=400, source_trust=0.1,
                       source_conflict=0.9, downstream_count=50),
                _entry(id="good_1", timestamp_age_days=1, source_trust=0.95,
                       source_conflict=0.02, downstream_count=1),
                _entry(id="good_2", timestamp_age_days=2, source_trust=0.9,
                       source_conflict=0.05, downstream_count=2),
            ],
            "action_type": "irreversible", "domain": "fintech",
        })
        j = r.json()
        if j["counterfactual_heal_suggested"]:
            assert j["counterfactual_top_entry_id"] == "bad_1"
            # Should be in repair_plan
            rp = j.get("repair_plan", [])
            cf_entries = [r for r in rp if r.get("counterfactual_source")]
            assert len(cf_entries) >= 1
            assert cf_entries[0]["entry_id"] == "bad_1"
            assert "counterfactual analysis" in cf_entries[0]["reason"]

    def test_single_entry_no_counterfactual(self):
        """Single entry can't do counterfactual (need 2+)."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        assert j["counterfactual_heal_suggested"] is False

    def test_is_boolean(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry(), _entry(id="cf_b2")],
            "action_type": "informational", "domain": "general",
        })
        assert isinstance(r.json()["counterfactual_heal_suggested"], bool)
