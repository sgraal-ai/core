"""Tests for Round 12 CC detector — confidence calibration detection."""
import os
import sys
import json

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.detection import _check_confidence_calibration
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}
CORPUS_PATH = os.path.join(os.path.dirname(__file__), "corpus", "round12", "round12_corpus.json")


def _load_cc_cases():
    with open(CORPUS_PATH) as f:
        data = json.load(f)
    return [c for c in data["cases"] if c["attack_family"] == "confidence_calibration"]


class TestStalenessConfidenceDivergence:
    def test_fresh_high_confidence_clean(self):
        entries = [
            {"id": "e1", "content": "fresh data", "type": "semantic",
             "timestamp_age_days": 1, "source_trust": 0.95, "model_confidence": 0.95},
            {"id": "e2", "content": "fresh data 2", "type": "semantic",
             "timestamp_age_days": 2, "source_trust": 0.90, "model_confidence": 0.92},
        ]
        result = _check_confidence_calibration(entries)
        assert not result["cc_signals"]["model_confidence_divergence"]

    def test_stale_high_confidence_divergent(self):
        entries = [
            {"id": "e1", "content": "old policy", "type": "policy",
             "timestamp_age_days": 150, "source_trust": 0.90, "model_confidence": 0.92},
            {"id": "e2", "content": "old policy 2", "type": "policy",
             "timestamp_age_days": 145, "source_trust": 0.88, "model_confidence": 0.92},
        ]
        result = _check_confidence_calibration(entries)
        assert result["cc_signals"]["model_confidence_divergence"]


class TestCorrelatedConsensus:
    def test_diverse_ages_not_correlated(self):
        entries = [
            {"id": "e1", "content": "a", "type": "semantic", "timestamp_age_days": 1, "source_trust": 0.9, "source_conflict": 0.1},
            {"id": "e2", "content": "b", "type": "semantic", "timestamp_age_days": 30, "source_trust": 0.85, "source_conflict": 0.05},
        ]
        result = _check_confidence_calibration(entries)
        assert not result["cc_signals"]["correlated_consensus"]

    def test_similar_ages_correlated(self):
        entries = [
            {"id": "e1", "content": "a", "type": "semantic", "timestamp_age_days": 50, "source_trust": 0.91, "source_conflict": 0.03},
            {"id": "e2", "content": "b", "type": "semantic", "timestamp_age_days": 50, "source_trust": 0.89, "source_conflict": 0.02},
            {"id": "e3", "content": "c", "type": "semantic", "timestamp_age_days": 51, "source_trust": 0.93, "source_conflict": 0.01},
        ]
        result = _check_confidence_calibration(entries)
        assert result["cc_signals"]["correlated_consensus"]


class TestStalButConfident:
    def test_tool_state_past_halflife(self):
        entries = [
            {"id": "e1", "content": "old tool", "type": "tool_state",
             "timestamp_age_days": 10, "source_trust": 0.9},
            {"id": "e2", "content": "old tool 2", "type": "tool_state",
             "timestamp_age_days": 12, "source_trust": 0.85},
        ]
        result = _check_confidence_calibration(entries)
        assert result["cc_signals"]["stale_but_confident_count"] >= 1


class TestGracefulDegradation:
    def test_no_model_confidence_still_checks_other_signals(self):
        entries = [
            {"id": "e1", "content": "test", "type": "policy",
             "timestamp_age_days": 200, "source_trust": 0.92},
            {"id": "e2", "content": "test2", "type": "policy",
             "timestamp_age_days": 195, "source_trust": 0.90},
        ]
        result = _check_confidence_calibration(entries)
        # No model_confidence → divergence=False, but sbc should fire
        assert not result["cc_signals"]["model_confidence_divergence"]
        assert result["cc_signals"]["stale_but_confident_count"] >= 1


class TestCCAttackDetection:
    def test_cc_overconfident_attacks_detected(self):
        """At least 3/5 CC overconfident attacks (authored BLOCK) should produce SUSPICIOUS or MANIPULATED.

        Originally 7 BLOCK attacks. CC-004 adjusted to ASK_USER (semantic content
        interpretation rule #4) and CC-007 adjusted to WARN (factual accuracy rule #1)
        during Phase 6 corpus recalibration. See CORPUS_RECALIBRATION.md.
        """
        cc_cases = _load_cc_cases()
        attacks = [c for c in cc_cases if not c["control"] and c["ground_truth"]["correct_decision"] == "BLOCK"]
        assert len(attacks) == 5, f"Expected 5 CC BLOCK attacks after Phase 6 recalibration, got {len(attacks)}"

        detected = 0
        for c in attacks:
            result = _check_confidence_calibration(c["memory_entries"])
            if result["confidence_calibration"] != "CLEAN":
                detected += 1

        assert detected >= 3, f"Only {detected}/5 CC BLOCK attacks detected (expected >=3)"


class TestCCControlCases:
    def test_no_cc_controls_manipulated(self):
        """No CC control should return MANIPULATED."""
        cc_cases = _load_cc_cases()
        controls = [c for c in cc_cases if c["control"]]

        manipulated = []
        for c in controls:
            result = _check_confidence_calibration(c["memory_entries"])
            if result["confidence_calibration"] == "MANIPULATED":
                manipulated.append(c["case_id"])

        assert not manipulated, f"CC controls MANIPULATED: {manipulated}"


class TestNoRegressionOnOtherFamilies:
    def test_legacy_entries_clean(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{"id": "m1", "content": "simple test", "type": "semantic",
                              "timestamp_age_days": 1, "source_trust": 0.9,
                              "source_conflict": 0.1, "downstream_count": 1}],
            "action_type": "reversible", "domain": "general", "dry_run": True,
        })
        assert r.status_code == 200
        d = r.json()
        assert d.get("confidence_calibration_check", "CLEAN") == "CLEAN"
