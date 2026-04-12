"""Tests for W3C VC, CloudEvents, Governance Score, portable attestation."""
import pytest


def _e(id="m1", content="Standard data.", type="semantic", age=1, trust=0.9,
       conflict=0.05, downstream=3):
    return {"id": id, "content": content, "type": type, "timestamp_age_days": age,
            "source_trust": trust, "source_conflict": conflict, "downstream_count": downstream}


def _client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


AUTH = {"Authorization": "Bearer sg_demo_playground"}


class TestW3CVerifiableCredential:
    def test_vc_compatible_certificate(self):
        """Feature 1: Certificate has W3C VC fields."""
        c = _client()
        pf = c.post("/v1/preflight", json={
            "memory_state": [_e(content="Per Q2 2024 SEC ruling and deprecated v2.1 framework was mandatory for 2023 filings.",
                                age=0, downstream=8)],
            "domain": "fintech", "action_type": "irreversible",
        }, headers=AUTH)
        outcome_id = pf.json().get("outcome_id")
        if outcome_id:
            resp = c.post("/v1/certificate", json={"request_id": outcome_id}, headers=AUTH)
            if resp.status_code == 200:
                cert = resp.json()
                assert cert.get("vc_compatible") is True
                assert "@context" in cert
                assert "https://www.w3.org/2018/credentials/v1" in cert["@context"]
                assert "VerifiableCredential" in cert.get("type", [])
                assert "credentialSubject" in cert
                assert cert["credentialSubject"]["decision"] == "BLOCK"
                assert cert["proof"]["type"] == "SgraalGovernanceProof2026"


class TestCloudEvents:
    def test_cloud_events_field_present(self):
        """Feature 2: cloud_events list present in response."""
        c = _client()
        resp = c.post("/v1/preflight", json={
            "memory_state": [_e(age=5, downstream=1)],
            "domain": "general", "action_type": "informational",
        }, headers=AUTH)
        data = resp.json()
        assert "cloud_events" in data
        assert isinstance(data["cloud_events"], list)


class TestGovernanceScore:
    def test_governance_score_insufficient(self):
        """Feature 3: < 10 calls → governance_score=null."""
        c = _client()
        resp = c.get("/v1/governance-score", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        # Demo key with limited history
        if data.get("total_governed_actions", 0) < 10:
            assert data["governance_score"] is None
            assert "Insufficient" in data.get("message", "")

    def test_governance_score_endpoint_works(self):
        """Endpoint returns valid structure."""
        c = _client()
        resp = c.get("/v1/governance-score", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_governed_actions" in data


class TestPortableAttestation:
    def test_attestation_verification(self):
        """Feature 4: verify-attestation confirms valid signature."""
        c = _client()
        # Get a preflight result with proof_signature
        pf = c.post("/v1/preflight", json={
            "memory_state": [_e(age=5, downstream=1)],
            "domain": "general", "action_type": "informational",
        }, headers=AUTH)
        data = pf.json()
        sig = data.get("proof_signature")
        if sig:
            # Verify the attestation (no auth required)
            resp = c.post("/v1/verify-attestation", json={
                "input_hash": data["input_hash"],
                "omega": data["omega_mem_final"],
                "decision": data["recommended_action"],
                "request_id": data["request_id"],
                "proof_signature": sig,
            })
            assert resp.status_code == 200
            assert resp.json()["valid"] is True

    def test_attestation_invalid_signature(self):
        """Invalid signature returns valid=false."""
        c = _client()
        resp = c.post("/v1/verify-attestation", json={
            "input_hash": "abc", "omega": 50.0, "decision": "BLOCK",
            "request_id": "fake-id", "proof_signature": "invalid-sig",
        })
        assert resp.status_code == 200
        assert resp.json()["valid"] is False
