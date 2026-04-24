"""Tests for 5 diagnostic response fields (#480-484)."""
import os
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

_CLEAN = [
    {"id": "e1", "content": "Clean memory entry for diagnostics", "type": "semantic",
     "timestamp_age_days": 5, "source_trust": 0.9, "source_conflict": 0.05, "downstream_count": 1}
]


def _preflight(entries=None, **kwargs):
    payload = {"memory_state": entries or _CLEAN, "action_type": "reversible",
               "domain": "general", "dry_run": True, **kwargs}
    return client.post("/v1/preflight", headers=AUTH, json=payload)


class TestRiskTypeShift:
    def test_field_present(self):
        r = _preflight(agent_id="diag_rts_1")
        assert "risk_type_shift" in r.json()

    def test_first_call_no_shift(self):
        r = _preflight(agent_id="diag_rts_2")
        rts = r.json()["risk_type_shift"]
        assert rts["shifted"] is False

    def test_has_expected_keys(self):
        r = _preflight(agent_id="diag_rts_3")
        rts = r.json()["risk_type_shift"]
        assert "shifted" in rts
        assert "from" in rts
        assert "to" in rts
        assert "magnitude" in rts


class TestDuplicateEntries:
    def test_no_duplicates(self):
        entries = [
            {"id": "a", "content": "Unique content A", "type": "semantic",
             "timestamp_age_days": 1, "source_trust": 0.9, "source_conflict": 0.05, "downstream_count": 1},
            {"id": "b", "content": "Unique content B", "type": "semantic",
             "timestamp_age_days": 1, "source_trust": 0.9, "source_conflict": 0.05, "downstream_count": 1},
        ]
        r = _preflight(entries, agent_id="diag_dup_1")
        assert r.json()["duplicate_entries"] == []

    def test_detects_duplicates(self):
        entries = [
            {"id": "a", "content": "Identical content for duplicate test", "type": "semantic",
             "timestamp_age_days": 1, "source_trust": 0.9, "source_conflict": 0.05, "downstream_count": 1},
            {"id": "b", "content": "Identical content for duplicate test", "type": "semantic",
             "timestamp_age_days": 1, "source_trust": 0.9, "source_conflict": 0.05, "downstream_count": 1},
        ]
        r = _preflight(entries, agent_id="diag_dup_2")
        dups = r.json()["duplicate_entries"]
        assert len(dups) == 1
        assert set(dups[0]) == {"a", "b"}


class TestRepairCalibrationError:
    def test_field_present_or_null(self):
        r = _preflight(agent_id="diag_rce_1")
        j = r.json()
        assert "repair_calibration_error" in j
        # First call has no previous data
        assert j["repair_calibration_error"] is None


class TestPeakDegradationHour:
    def test_field_present_or_null(self):
        r = _preflight(agent_id="diag_pdh_1")
        j = r.json()
        assert "peak_degradation_hour" in j
        # Likely null without enough history
        if j["peak_degradation_hour"] is not None:
            assert "peak_hour_utc" in j["peak_degradation_hour"]
            assert "peak_omega_avg" in j["peak_degradation_hour"]


class TestCounterfactualBlockValue:
    def test_field_present_or_null(self):
        r = _preflight(agent_id="diag_cbv_1")
        j = r.json()
        assert "counterfactual_block_value" in j
        # Likely null without BLOCK history
        if j["counterfactual_block_value"] is not None:
            assert "fleet_block_count" in j["counterfactual_block_value"]
            assert "value_rate" in j["counterfactual_block_value"]


class TestDiagnosticFieldsDoNotAffectDecision:
    def test_decision_unchanged(self):
        """Diagnostic fields must not change the recommended_action."""
        r1 = _preflight(agent_id="diag_invariance_1")
        r2 = _preflight(agent_id="diag_invariance_2")
        assert r1.json()["recommended_action"] == r2.json()["recommended_action"]
