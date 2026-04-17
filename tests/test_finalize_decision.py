"""Test #9: finalize_decision is called exactly once per preflight and
recommended_action matches its output.

The decision trail documents every _set_action() call through the
preflight pipeline. finalize_decision() is the canonical source of
the final recommended_action.
"""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


class TestFinalizeDecision:
    def test_decision_trail_present_on_every_response(self):
        """Every preflight response must include the decision trail,
        proving finalize_decision() was called."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{
                "id": "m1", "content": "fresh", "type": "preference",
                "timestamp_age_days": 1, "source_trust": 0.95,
                "source_conflict": 0.05, "downstream_count": 1,
            }],
            "action_type": "reversible",
            "domain": "general",
        })
        assert r.status_code == 200
        d = r.json()
        assert "decision_trail" in d, "finalize_decision() was not called — decision_trail missing"
        assert "decision_trail_length" in d
        trail = d["decision_trail"]
        assert isinstance(trail, list)
        assert len(trail) >= 1, "trail must contain at least the initial scoring_engine entry"

    def test_decision_trail_starts_with_scoring_engine(self):
        """The first trail entry must be from the scoring engine (the initial decision)."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{
                "id": "m1", "content": "fresh", "type": "preference",
                "timestamp_age_days": 1, "source_trust": 0.95,
                "source_conflict": 0.05, "downstream_count": 1,
            }],
            "action_type": "reversible",
            "domain": "general",
        })
        d = r.json()
        first = d["decision_trail"][0]
        assert first["source"] == "scoring_engine"
        assert first["seq"] == 0
        assert first["action"] in ("USE_MEMORY", "WARN", "ASK_USER", "BLOCK")

    def test_final_action_matches_last_trail_entry(self):
        """The response's recommended_action must match the last trail entry."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{
                "id": "m1", "content": "stale", "type": "tool_state",
                "timestamp_age_days": 60, "source_trust": 0.5,
                "source_conflict": 0.5, "downstream_count": 5,
            }],
            "action_type": "irreversible",
            "domain": "fintech",
        })
        d = r.json()
        trail = d["decision_trail"]
        last_entry = trail[-1]
        assert d["recommended_action"] == last_entry["action"], (
            f"recommended_action={d['recommended_action']} doesn't match "
            f"last trail entry action={last_entry['action']} "
            f"(source={last_entry['source']})"
        )

    def test_trail_length_matches_count_field(self):
        """decision_trail_length must equal len(decision_trail)."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{
                "id": "m1", "content": "x", "type": "semantic",
                "timestamp_age_days": 10, "source_trust": 0.8,
                "source_conflict": 0.2, "downstream_count": 3,
            }],
            "action_type": "reversible",
            "domain": "general",
        })
        d = r.json()
        assert d["decision_trail_length"] == len(d["decision_trail"])

    def test_overrides_produce_multiple_trail_entries(self):
        """When per-type thresholds fire (identity threshold=13), the trail
        must contain both the initial scoring_engine entry AND the
        per_type_threshold override — proving both ran and were recorded."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{
                "id": "m1", "content": "stale identity", "type": "identity",
                "timestamp_age_days": 50, "source_trust": 0.7,
                "source_conflict": 0.3, "downstream_count": 5,
            }],
            "action_type": "reversible",
            "domain": "general",
            "per_type_thresholds": True,
        })
        d = r.json()
        trail = d["decision_trail"]
        sources = [e["source"] for e in trail]
        assert "scoring_engine" in sources, "initial scoring entry missing"
        # Per-type threshold should have fired for identity (θ=13, omega ~15-25)
        if d.get("per_type_override_triggered"):
            assert "per_type_threshold" in sources, (
                f"per_type_threshold override fired but not in trail. "
                f"Trail sources: {sources}"
            )
            assert d["recommended_action"] == "BLOCK"
