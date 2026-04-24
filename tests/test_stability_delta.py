"""Tests for stability_delta Lyapunov analog field in preflight response."""
import os
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

_CLEAN = [
    {"id": "e1", "content": "Clean entry", "type": "semantic",
     "timestamp_age_days": 5, "source_trust": 0.9, "source_conflict": 0.05, "downstream_count": 1}
]


class TestStabilityDelta:
    def test_first_call_returns_stable(self):
        """First call for an agent has no previous state → stable with note."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _CLEAN,
            "action_type": "reversible",
            "domain": "general",
            "agent_id": "stability_test_first",
            "dry_run": True,
        })
        assert r.status_code == 200
        j = r.json()
        assert "stability_delta" in j
        assert j["stability_delta"] == 0.0
        assert j["stability_trend"] == "stable"

    def test_delta_is_float(self):
        """stability_delta must be a float in [-1, +1]."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _CLEAN,
            "action_type": "reversible",
            "domain": "general",
            "agent_id": "stability_test_type",
            "dry_run": True,
        })
        j = r.json()
        delta = j.get("stability_delta")
        assert isinstance(delta, (int, float))
        assert -1.0 <= delta <= 1.0

    def test_trend_is_valid_enum(self):
        """stability_trend must be one of the 3 valid values."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _CLEAN,
            "action_type": "reversible",
            "domain": "general",
            "agent_id": "stability_test_enum",
            "dry_run": True,
        })
        j = r.json()
        assert j["stability_trend"] in ("stabilizing", "stable", "destabilizing")

    def test_does_not_affect_decision(self):
        """stability_delta is informational — same memory state must produce
        same recommended_action regardless of stability_delta value."""
        r1 = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _CLEAN,
            "action_type": "reversible",
            "domain": "general",
            "agent_id": "stability_test_decision",
            "dry_run": True,
        })
        r2 = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _CLEAN,
            "action_type": "reversible",
            "domain": "general",
            "agent_id": "stability_test_decision",
            "dry_run": True,
        })
        assert r1.json()["recommended_action"] == r2.json()["recommended_action"]
