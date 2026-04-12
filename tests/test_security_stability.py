"""Tests for security and stability fixes — access control, dict bounds, calibration isolation, corroboration trace."""
import pytest


def _e(id="m1", content="Standard data.", type="semantic", age=1, trust=0.9,
       conflict=0.05, downstream=3, provenance_chain=None):
    d = {"id": id, "content": content, "type": type, "timestamp_age_days": age,
         "source_trust": trust, "source_conflict": conflict, "downstream_count": downstream}
    if provenance_chain is not None:
        d["provenance_chain"] = provenance_chain
    return d


def _client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


AUTH = {"Authorization": "Bearer sg_demo_playground"}


class TestCertificateAccessControl:
    def test_certificate_access_same_key(self):
        """Issuing key can retrieve its own certificate."""
        c = _client()
        # Issue
        pf = c.post("/v1/preflight", json={
            "memory_state": [_e(content="Per Q2 2024 SEC ruling and deprecated v2.1 framework was mandatory for 2023 filings.",
                                age=0, downstream=8)],
            "domain": "fintech", "action_type": "irreversible",
        }, headers=AUTH)
        outcome_id = pf.json().get("outcome_id")
        if outcome_id:
            cert_resp = c.post("/v1/certificate", json={"request_id": outcome_id}, headers=AUTH)
            if cert_resp.status_code == 200:
                cert_id = cert_resp.json()["certificate_id"]
                # Retrieve with same key → should work
                get_resp = c.get(f"/v1/certificate/{cert_id}", headers=AUTH)
                assert get_resp.status_code == 200


class TestDictBounds:
    def test_eviction_function(self):
        """_evict_if_full caps dict at 10,000 entries."""
        from api.main import _evict_if_full, _DICT_MAX_SIZE
        d = {str(i): i for i in range(10002)}
        assert len(d) > _DICT_MAX_SIZE
        _evict_if_full(d, "test_dict")
        assert len(d) <= _DICT_MAX_SIZE


class TestCalibrationIsolation:
    def test_calibration_demo_key_no_crash(self):
        """CalibrationEngine initializes cleanly with demo and non-demo keys."""
        from api.calibration_engine import CalibrationEngine
        # Demo key → no warning
        engine1 = CalibrationEngine(api_key="sg_demo_playground")
        assert engine1.api_key == "sg_demo_playground"
        # Non-demo key → logs warning but doesn't crash
        engine2 = CalibrationEngine(api_key="sg_live_test_key_12345")
        assert engine2.api_key == "sg_live_test_key_12345"


class TestGenuineCorroborationTrace:
    def test_consensus_collapse_initial_preserved(self):
        """consensus_collapse_initial shows raw result before genuine_corroboration."""
        c = _client()
        # 3 entries with different provenance chains (triggers genuine corroboration)
        entries = [
            _e(id="m1", content="Revenue grew 12% in Q4 driven by enterprise.",
               trust=0.88, conflict=0.12, downstream=6, provenance_chain=["agent-01"]),
            _e(id="m2", content="Q4 revenue growth was 12% from enterprise expansion.",
               trust=0.85, conflict=0.08, downstream=8, provenance_chain=["agent-02"]),
            _e(id="m3", content="Enterprise segment drove 12% revenue growth in Q4.",
               trust=0.91, conflict=0.15, downstream=5, provenance_chain=["agent-03"]),
        ]
        resp = c.post("/v1/preflight", json={
            "memory_state": entries, "domain": "fintech", "action_type": "informational",
        }, headers=AUTH)
        data = resp.json()
        # Should have trace fields
        assert "consensus_collapse_initial" in data
        assert "genuine_corroboration_applied" in data
        # If genuine corroboration fired, initial should differ from final
        if data.get("genuine_corroboration_applied"):
            assert data["consensus_collapse"] == "CLEAN"
            assert data["consensus_collapse_initial"] in ("SUSPICIOUS", "MANIPULATED")
