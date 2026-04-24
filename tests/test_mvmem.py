"""Tests for POST /v1/mvmem — minimum viable memory."""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


class TestMvmemAllEssential:
    def test_single_entry_is_essential(self):
        """A single entry cannot be removed — it's always essential."""
        r = client.post("/v1/mvmem", headers=AUTH, json={
            "memory_state": [
                {"id": "e1", "content": "Critical system config", "type": "semantic",
                 "source_conflict": 0.1, "timestamp_age_days": 1},
            ],
            "action_type": "reversible",
            "domain": "general",
        })
        assert r.status_code == 200
        d = r.json()
        assert "original_decision" in d
        assert "original_omega" in d
        assert "minimum_subset" in d
        assert "removable_entries" in d
        assert "estimated_savings" in d
        # Single entry should be in minimum_subset (essential)
        assert "e1" in d["minimum_subset"]
        assert len(d["removable_entries"]) == 0


class TestMvmemSomeRemovable:
    def test_redundant_entries_removable(self):
        """When entries are redundant, some should be identified as removable."""
        # Create a set of entries where some are clearly redundant
        _entries = [
            {"id": f"r{i}", "content": f"Memory entry {i} with some content", "type": "semantic",
             "source_conflict": 0.1, "timestamp_age_days": 1}
            for i in range(5)
        ]
        r = client.post("/v1/mvmem", headers=AUTH, json={
            "memory_state": _entries,
            "action_type": "reversible",
            "domain": "general",
        })
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["minimum_subset"], list)
        assert isinstance(d["removable_entries"], list)
        # Total should equal original count
        assert len(d["minimum_subset"]) + len(d["removable_entries"]) == 5
        assert d["estimated_savings"]["entries_removed"] == len(d["removable_entries"])
        if d["removable_entries"]:
            assert d["estimated_savings"]["percent"] > 0


class TestMvmemEmptyState:
    def test_empty_memory_state(self):
        """Empty memory state returns empty result."""
        r = client.post("/v1/mvmem", headers=AUTH, json={
            "memory_state": [],
            "action_type": "reversible",
            "domain": "general",
        })
        assert r.status_code == 200
        d = r.json()
        assert d["original_decision"] == "USE_MEMORY"
        assert d["original_omega"] == 0
        assert d["minimum_subset"] == []
        assert d["removable_entries"] == []
        assert d["estimated_savings"]["entries_removed"] == 0
        assert d["estimated_savings"]["percent"] == 0
