"""Tests for #783 written_by_current_agent schema field (Phase 1 — schema only)."""
import os
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def _entry(**kw):
    base = {"id": "e1", "content": "Test entry", "type": "semantic",
            "timestamp_age_days": 5, "source_trust": 0.9,
            "source_conflict": 0.05, "downstream_count": 1}
    base.update(kw)
    return base


class TestWrittenByCurrentAgent:
    def test_field_none_by_default(self):
        """Omitting the field should produce the same result as before."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "reversible", "domain": "general", "dry_run": True,
        })
        assert r.status_code == 200
        assert r.json()["recommended_action"] in ("USE_MEMORY", "WARN", "ASK_USER", "BLOCK")

    def test_field_true_accepted(self):
        """Setting written_by_current_agent=True should be accepted."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry(written_by_current_agent=True)],
            "action_type": "reversible", "domain": "general", "dry_run": True,
        })
        assert r.status_code == 200

    def test_field_false_accepted(self):
        """Setting written_by_current_agent=False should be accepted."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry(written_by_current_agent=False)],
            "action_type": "reversible", "domain": "general", "dry_run": True,
        })
        assert r.status_code == 200

    def test_field_does_not_change_decision(self):
        """Phase 1: the field should NOT change the scoring decision."""
        r_none = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "reversible", "domain": "general", "dry_run": True,
        })
        r_true = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry(written_by_current_agent=True)],
            "action_type": "reversible", "domain": "general", "dry_run": True,
        })
        r_false = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry(written_by_current_agent=False)],
            "action_type": "reversible", "domain": "general", "dry_run": True,
        })
        assert r_none.json()["recommended_action"] == r_true.json()["recommended_action"]
        assert r_none.json()["recommended_action"] == r_false.json()["recommended_action"]

    def test_backward_compatibility(self):
        """Requests without the field should work identically to before."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{"id": "e1", "content": "Old format entry", "type": "semantic",
                              "timestamp_age_days": 5, "source_trust": 0.9,
                              "source_conflict": 0.05, "downstream_count": 1}],
            "action_type": "reversible", "domain": "general", "dry_run": True,
        })
        assert r.status_code == 200
        assert "recommended_action" in r.json()
