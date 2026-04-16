"""Tests for Task 4: Sgraal Certified Memory (W3C Verifiable Credential)."""
import os
import sys
import time

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

_HEALTHY = [{
    "id": "m1",
    "content": "Fresh customer preference",
    "type": "preference",
    "timestamp_age_days": 1,
    "source_trust": 0.95,
    "source_conflict": 0.05,
    "downstream_count": 1,
}]

_STALE_HIGH_RISK = [{
    "id": "m1",
    "content": "Stale conflicting tool state",
    "type": "tool_state",
    "timestamp_age_days": 180,
    "source_trust": 0.2,
    "source_conflict": 0.8,
    "downstream_count": 5,
}]


class TestCertify:
    def test_healthy_memory_certified(self):
        r = client.post(
            "/v1/certify",
            headers=AUTH,
            json={"agent_id": "agent_a", "memory_state": _HEALTHY, "scope": "preflight"},
        )
        assert r.status_code == 200
        d = r.json()
        assert d["certified"] is True
        c = d["credential"]
        assert "VerifiableCredential" in c["type"]
        assert "SgraalMemoryCredential" in c["type"]
        assert c["issuer"] == "https://api.sgraal.com"
        assert c["credentialSubject"]["agent_id"] == "agent_a"
        assert c["credentialSubject"]["decision"] in ("USE_MEMORY", "WARN")
        assert c["credentialSubject"]["valid_for_seconds"] == 300
        assert c["proof"]["type"] == "SgraalProof2026"
        assert len(c["proof"]["proofValue"]) == 64  # SHA-256 hex

    def test_block_memory_not_certified(self):
        r = client.post(
            "/v1/certify",
            headers=AUTH,
            json={
                "agent_id": "agent_b",
                "memory_state": _STALE_HIGH_RISK,
                "scope": "preflight",
                "action_type": "irreversible",
                "domain": "fintech",
            },
        )
        assert r.status_code == 200
        d = r.json()
        # Stale high-risk data in fintech/irreversible should be BLOCK or ASK_USER
        assert d["certified"] is False
        assert "reason" in d
        assert d["decision"] in ("BLOCK", "ASK_USER")

    def test_verify_valid_certificate(self):
        r1 = client.post(
            "/v1/certify",
            headers=AUTH,
            json={"agent_id": "agent_c", "memory_state": _HEALTHY, "scope": "preflight"},
        )
        assert r1.status_code == 200
        cert = r1.json()["credential"]

        r2 = client.post(
            "/v1/certify/verify",
            headers=AUTH,
            json={"certificate": cert},
        )
        assert r2.status_code == 200
        d = r2.json()
        assert d["valid"] is True
        assert d["expired"] is False
        assert d["reason"] == "Valid credential"
        assert d["omega"] == cert["credentialSubject"]["omega"]

    def test_verify_tampered_certificate_rejected(self):
        r1 = client.post(
            "/v1/certify",
            headers=AUTH,
            json={"agent_id": "agent_d", "memory_state": _HEALTHY, "scope": "preflight"},
        )
        assert r1.status_code == 200
        cert = r1.json()["credential"]

        # Tamper: change agent_id (guaranteed to differ from "agent_d" used at issue)
        original_agent = cert["credentialSubject"]["agent_id"]
        cert["credentialSubject"]["agent_id"] = "attacker_impersonating"
        assert cert["credentialSubject"]["agent_id"] != original_agent

        r2 = client.post(
            "/v1/certify/verify",
            headers=AUTH,
            json={"certificate": cert},
        )
        assert r2.status_code == 200
        d = r2.json()
        assert d["valid"] is False
        assert "HMAC" in d["reason"] or "tampered" in d["reason"].lower()

    def test_verify_tampered_omega_rejected(self):
        r1 = client.post(
            "/v1/certify",
            headers=AUTH,
            json={"agent_id": "agent_d2", "memory_state": _HEALTHY, "scope": "preflight"},
        )
        assert r1.status_code == 200
        cert = r1.json()["credential"]

        # Tamper: bump omega to a clearly different value (original healthy memory ≈ 0)
        original_omega = cert["credentialSubject"]["omega"]
        cert["credentialSubject"]["omega"] = original_omega + 50.0
        assert cert["credentialSubject"]["omega"] != original_omega

        r2 = client.post(
            "/v1/certify/verify",
            headers=AUTH,
            json={"certificate": cert},
        )
        assert r2.status_code == 200
        d = r2.json()
        assert d["valid"] is False
        assert "HMAC" in d["reason"] or "tampered" in d["reason"].lower()

    def test_verify_expired_certificate(self):
        r1 = client.post(
            "/v1/certify",
            headers=AUTH,
            json={
                "agent_id": "agent_e",
                "memory_state": _HEALTHY,
                "scope": "preflight",
                "valid_for_seconds": 1,  # 1-second TTL
            },
        )
        assert r1.status_code == 200
        cert = r1.json()["credential"]

        # Wait for expiry
        time.sleep(1.2)

        r2 = client.post(
            "/v1/certify/verify",
            headers=AUTH,
            json={"certificate": cert},
        )
        assert r2.status_code == 200
        d = r2.json()
        assert d["valid"] is False
        assert d["expired"] is True

    def test_verify_malformed_certificate(self):
        r = client.post(
            "/v1/certify/verify",
            headers=AUTH,
            json={"certificate": {}},
        )
        assert r.status_code == 200
        d = r.json()
        assert d["valid"] is False
        assert "malformed" in d["reason"].lower() or "missing" in d["reason"].lower()

    def test_certify_get_verify_returns_405(self):
        r = client.get("/v1/certify/verify", headers=AUTH)
        assert r.status_code == 405
        assert "POST" in r.json()["detail"]
