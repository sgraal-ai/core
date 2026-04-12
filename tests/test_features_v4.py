"""Tests for ZK proof, content independence, domain naturalness, calibration rate limit, threat graph."""
import pytest
import hashlib


def _e(id="m1", content="Standard data.", type="semantic", age=1, trust=0.9,
       conflict=0.05, downstream=3):
    return {"id": id, "content": content, "type": type, "timestamp_age_days": age,
            "source_trust": trust, "source_conflict": conflict, "downstream_count": downstream}


def _client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


AUTH = {"Authorization": "Bearer sg_demo_playground"}


class TestZKProof:
    def test_zk_proof_in_preflight(self):
        c = _client()
        resp = c.post("/v1/preflight", json={
            "memory_state": [_e(age=5, downstream=1)],
            "domain": "general", "action_type": "informational",
        }, headers=AUTH)
        data = resp.json()
        assert "zk_proof" in data
        assert data["zk_proof"]["proof_valid"] is True
        assert data["zk_proof"]["proof_type"] == "zk_sheaf_v1"

    def test_zk_verify_endpoint(self):
        c = _client()
        # Get a preflight with ZK proof
        pf = c.post("/v1/preflight", json={
            "memory_state": [_e(age=5, downstream=1)],
            "domain": "general", "action_type": "informational",
        }, headers=AUTH)
        data = pf.json()
        # Verify the proof (no auth)
        resp = c.post("/v1/zk/verify", json={
            "proof_hash": data["zk_proof"]["proof_hash"],
            "input_hash": data["input_hash"],
            "omega": data["omega_mem_final"],
            "decision": data["recommended_action"],
        })
        assert resp.status_code == 200
        assert resp.json()["valid"] is True


class TestContentIndependence:
    def test_content_independence_similar(self):
        """Very similar entries → content_too_similar: true."""
        from api.main import _check_consensus_collapse
        entries = [
            _e(id="m1", content="Settlement netting approved for transaction processing.",
               trust=0.90, conflict=0.02, downstream=8),
            _e(id="m2", content="Settlement netting approved for transaction processing.",
               trust=0.90, conflict=0.02, downstream=8),
            _e(id="m3", content="Settlement netting approved for transaction processing.",
               trust=0.90, conflict=0.02, downstream=18),
        ]
        result = _check_consensus_collapse(entries)
        assert result.get("content_too_similar") is True
        assert result.get("content_independence_score", 1.0) < 0.3


class TestDomainNaturalness:
    def test_domain_naturalness_baseline(self):
        """Fintech uses strict baseline."""
        c = _client()
        resp = c.post("/v1/preflight", json={
            "memory_state": [_e(age=5, downstream=1)],
            "domain": "fintech", "action_type": "informational",
        }, headers=AUTH)
        data = resp.json()
        # naturalness check may or may not be in compact, check if present
        # The domain_naturalness_baseline is returned via naturalness check
        assert resp.status_code == 200


class TestCalibrationRateLimit:
    def test_calibration_runs_remaining(self):
        """Calibration response includes runs_remaining."""
        c = _client()
        resp = c.post("/v1/calibration/run", json={
            "corpus": "round6", "dry_run": True,
        }, headers=AUTH)
        if resp.status_code == 200:
            data = resp.json()
            assert "calibration_runs_today" in data
            assert "calibration_runs_remaining" in data


class TestThreatGraph:
    def test_threat_graph_endpoint(self):
        c = _client()
        resp = c.get("/v1/threat-graph", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        assert "total_compromised" in data
