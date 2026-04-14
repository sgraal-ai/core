"""Tests for GET /v1/insights endpoint."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app, _outcomes, _outcome_set

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def _seed_outcome(agent_id="test-agent-insights"):
    """Seed an outcome with memory_state so /v1/insights has data."""
    # Run a preflight to create an outcome
    r = client.post("/v1/preflight", headers=AUTH, json={
        "memory_state": [
            {"id": "ins_1", "content": "Customer support FAQ", "type": "semantic",
             "timestamp_age_days": 15, "source_trust": 0.8, "source_conflict": 0.15, "downstream_count": 5},
            {"id": "ins_2", "content": "API rate limit config", "type": "tool_state",
             "timestamp_age_days": 2, "source_trust": 0.9, "source_conflict": 0.05, "downstream_count": 3},
        ],
        "action_type": "reversible",
        "domain": "general",
        "agent_id": agent_id,
    })
    assert r.status_code == 200
    return r.json()


class TestInsightsEndpoint:
    def test_returns_200_with_seeded_data(self):
        _seed_outcome("insights-agent-1")
        r = client.get("/v1/insights?agent_id=insights-agent-1", headers=AUTH)
        assert r.status_code == 200
        j = r.json()
        assert j["available"] is True
        assert j["agent_id"] == "insights-agent-1"

    def test_unavailable_without_data(self):
        r = client.get("/v1/insights?agent_id=nonexistent-agent-xyz", headers=AUTH)
        assert r.status_code == 200
        j = r.json()
        assert j["available"] is False
        assert j["reason"] == "no_recent_data"

    def test_requires_agent_id(self):
        r = client.get("/v1/insights", headers=AUTH)
        assert r.status_code == 400

    def test_requires_auth(self):
        r = client.get("/v1/insights?agent_id=test")
        assert r.status_code in (401, 403)

    def test_all_synthesis_fields_present(self):
        _seed_outcome("insights-agent-2")
        r = client.get("/v1/insights?agent_id=insights-agent-2", headers=AUTH)
        j = r.json()
        assert j["available"] is True
        expected_fields = [
            "days_until_block", "days_until_block_confidence",
            "confidence_calibration", "knowledge_age_days", "knowledge_age_std_days",
            "top_heal_roi_entry_id", "top_heal_roi_value",
            "fleet_health_distance", "fleet_health_distance_available",
            "memory_complexity_trend", "cost_adjusted_decision",
            "single_point_of_failure_entry_id", "single_point_of_failure_score",
            "monoculture_risk_score", "monoculture_risk_level",
            "omega_mem_final", "recommended_action",
            "insight_summary", "generated_at",
        ]
        for field in expected_fields:
            assert field in j, f"Missing field: {field}"

    def test_insight_summary_is_string(self):
        _seed_outcome("insights-agent-3")
        r = client.get("/v1/insights?agent_id=insights-agent-3", headers=AUTH)
        j = r.json()
        assert isinstance(j["insight_summary"], str)
        assert len(j["insight_summary"]) > 0

    def test_confidence_calibration_structure(self):
        _seed_outcome("insights-agent-4")
        r = client.get("/v1/insights?agent_id=insights-agent-4", headers=AUTH)
        cc = r.json()["confidence_calibration"]
        assert "state" in cc
        assert "score" in cc
        assert cc["state"] in ("OVERCONFIDENT", "UNDERCONFIDENT", "CALIBRATED")

    def test_generated_at_is_iso_timestamp(self):
        _seed_outcome("insights-agent-5")
        r = client.get("/v1/insights?agent_id=insights-agent-5", headers=AUTH)
        ts = r.json()["generated_at"]
        assert "T" in ts
        assert "20" in ts  # year prefix
