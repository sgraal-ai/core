"""Tests for 4 preflight response improvements:
- #455 days_until_block_ci (95% CI + confidence across 4 models)
- #456 confidence_calibration_explanation (human-readable)
- #457 knowledge_age_summary (effective age ± uncertainty + oldest trusted)
- #458 repair_plan ranking (rank, roi_percentile, repair_plan_summary)
"""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


_STALE_MULTI = [
    {"id": "m1", "content": "x", "type": "tool_state", "timestamp_age_days": 45,
     "source_trust": 0.6, "source_conflict": 0.4, "downstream_count": 2},
    {"id": "m2", "content": "y", "type": "tool_state", "timestamp_age_days": 25,
     "source_trust": 0.8, "source_conflict": 0.2, "downstream_count": 3},
]
_SCORE_HISTORY_RISING = [40, 42, 45, 48, 50, 52, 55, 58, 60, 62]

_HEALTHY_SINGLE = [{
    "id": "m1", "content": "fresh", "type": "preference",
    "timestamp_age_days": 1, "source_trust": 0.95, "source_conflict": 0.05, "downstream_count": 1,
}]


class TestDaysUntilBlockCI:
    def test_days_until_block_ci_structure(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _STALE_MULTI,
            "action_type": "reversible",
            "domain": "general",
            "score_history": _SCORE_HISTORY_RISING,
        })
        assert r.status_code == 200
        d = r.json()
        # Should have both the point estimate and the CI when multiple models fire
        assert "days_until_block" in d
        assert "days_until_block_ci" in d
        ci = d["days_until_block_ci"]
        if ci is not None:
            assert "low" in ci and "high" in ci
            assert ci["low"] <= ci["high"]
            # CI must contain the point estimate
            assert ci["low"] <= d["days_until_block"] <= ci["high"]

    def test_days_until_block_confidence_in_range(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _STALE_MULTI,
            "action_type": "reversible",
            "domain": "general",
            "score_history": _SCORE_HISTORY_RISING,
        })
        d = r.json()
        conf = d.get("days_until_block_confidence")
        if conf is not None:
            assert 0.0 <= conf <= 1.0

    def test_days_until_block_zero_when_already_blocked(self):
        # High-risk memory — should already be at/above BLOCK threshold
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{
                "id": "m1", "content": "x", "type": "tool_state",
                "timestamp_age_days": 200, "source_trust": 0.1,
                "source_conflict": 0.9, "downstream_count": 10,
            }],
            "action_type": "irreversible",
            "domain": "fintech",
        })
        d = r.json()
        if d.get("recommended_action") == "BLOCK":
            # Already-blocked path sets days to 0 with confidence 1.0
            assert d["days_until_block"] == 0.0
            assert d["days_until_block_confidence"] == 1.0


class TestConfidenceCalibrationExplanation:
    def test_explanation_field_present_and_non_empty(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _HEALTHY_SINGLE,
            "action_type": "reversible",
            "domain": "general",
        })
        d = r.json()
        assert "confidence_calibration" in d
        cc = d["confidence_calibration"]
        assert "explanation" in cc
        assert isinstance(cc["explanation"], str)
        assert len(cc["explanation"]) > 20
        # Also mirrored at response root
        assert d.get("confidence_calibration_explanation") == cc["explanation"]

    def test_explanation_references_actual_values(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _HEALTHY_SINGLE,
            "action_type": "reversible",
            "domain": "general",
        })
        d = r.json()
        explanation = d["confidence_calibration"]["explanation"]
        # Explanation should include at least one of the 3 concrete metrics by name
        assert any(key in explanation for key in ["r_belief", "s_drift", "H¹", "H1"])


class TestKnowledgeAgeSummary:
    def test_summary_string_present_and_formatted(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _STALE_MULTI,
            "action_type": "reversible",
            "domain": "general",
        })
        d = r.json()
        assert "knowledge_age_summary" in d
        summary = d["knowledge_age_summary"]
        assert summary is not None
        assert "days old" in summary
        assert "±" in summary
        assert "Oldest trusted entry" in summary

    def test_oldest_trusted_entry_reported(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _STALE_MULTI,
            "action_type": "reversible",
            "domain": "general",
        })
        d = r.json()
        oldest = d.get("knowledge_age_oldest_trusted_days")
        # STALE_MULTI has entries aged 45 and 25 both with trust >= 0.5 → oldest trusted = 45
        assert oldest == 45.0


class TestRepairPlanRanking:
    def test_rank_and_percentile_on_each_entry(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _STALE_MULTI,
            "action_type": "reversible",
            "domain": "general",
            "score_history": _SCORE_HISTORY_RISING,
        })
        d = r.json()
        rp = d.get("repair_plan", [])
        if not rp:
            return  # no repair plan means nothing to rank
        # Ranks must be 1, 2, 3... in order (since plan is sorted by ROI descending)
        for i, item in enumerate(rp):
            assert item.get("rank") == i + 1, f"rank mismatch at index {i}"
            assert 0.0 <= item.get("roi_percentile", 0) <= 100.0
        # First entry is highest ROI → percentile 100 when n > 1
        if len(rp) > 1:
            assert rp[0]["roi_percentile"] == 100.0

    def test_repair_plan_summary_string(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _STALE_MULTI,
            "action_type": "reversible",
            "domain": "general",
            "score_history": _SCORE_HISTORY_RISING,
        })
        d = r.json()
        summary = d.get("repair_plan_summary")
        assert summary is not None
        rp = d.get("repair_plan", [])
        if rp:
            # Summary references a rank and the action or heal entry
            assert "Heal entry" in summary or "highest ROI" in summary
            assert "rank 1 of" in summary
        else:
            assert "healthy" in summary.lower()
