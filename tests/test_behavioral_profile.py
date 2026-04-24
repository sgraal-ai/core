"""Tests for GET /v1/agent/{agent_id}/behavioral-profile."""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from fastapi.testclient import TestClient
from api.main import app, _outcomes, _outcomes_lock
from api.redis_state import redis_delete
import hashlib

client = TestClient(app)
AUTH_1 = {"Authorization": "Bearer sg_test_key_001"}
AUTH_2 = {"Authorization": "Bearer sg_test_key_002"}

# Test keys use sha256 of the API key string as key_hash
_KH_1 = hashlib.sha256("sg_test_key_001".encode()).hexdigest()
_KH_2 = hashlib.sha256("sg_test_key_002".encode()).hexdigest()


def _inject_outcomes(agent_id: str, key_hash: str, count: int = 5, domain: str = "general",
                     action: str = "USE_MEMORY", omega: float = 25.0):
    """Inject synthetic outcomes for testing."""
    # Clear any cached behavioral profile first
    try:
        redis_delete(f"behavioral_profile:{key_hash}:{agent_id}")
    except Exception:
        pass
    import uuid
    ids = []
    with _outcomes_lock:
        for i in range(count):
            oid = f"bp_test_{uuid.uuid4().hex[:8]}"
            _outcomes[oid] = {
                "request_id": oid,
                "agent_id": agent_id,
                "key_hash": key_hash,
                "domain": domain,
                "recommended_action": action,
                "omega_mem_final": omega + i,
                "action_type": "reversible",
                "created_at": datetime(2026, 4, 24, 10 + (i % 12), 30, tzinfo=timezone.utc).isoformat(),
                "status": "open",
            }
            ids.append(oid)
    return ids


def _cleanup_outcomes(ids: list, agent_id: str = None, key_hash: str = None):
    """Remove injected outcomes and clear Redis cache."""
    with _outcomes_lock:
        for oid in ids:
            _outcomes.pop(oid, None)
    if agent_id and key_hash:
        try:
            redis_delete(f"behavioral_profile:{key_hash}:{agent_id}")
        except Exception:
            pass


class TestBehavioralProfileEmpty:
    def test_empty_agent_returns_nulls(self):
        """Agent with no outcomes returns null/empty fields, not 404."""
        r = client.get("/v1/agent/nonexistent_agent_xyz/behavioral-profile", headers=AUTH_1)
        assert r.status_code == 200
        d = r.json()
        assert d["agent_id"] == "nonexistent_agent_xyz"
        assert d["call_frequency"]["hourly"] == []
        assert d["call_frequency"]["daily"] == []
        assert d["action_escalation"]["ratio"] is None
        assert d["action_escalation"]["trend"] is None
        assert d["domain_switching"]["primary"] is None
        assert d["omega_history"]["mean"] is None
        assert d["omega_history"]["samples"] == 0


class TestBehavioralProfilePopulated:
    def test_populated_agent_returns_data(self):
        """Agent with outcomes returns computed behavioral profile."""
        _agent_id = "bp_test_agent_populated"
        ids = _inject_outcomes(_agent_id, _KH_1, count=6, omega=20.0)
        try:
            r = client.get(f"/v1/agent/{_agent_id}/behavioral-profile", headers=AUTH_1)
            assert r.status_code == 200
            d = r.json()
            assert d["agent_id"] == _agent_id
            assert d["omega_history"]["samples"] == 6
            assert d["omega_history"]["mean"] is not None
            assert d["omega_history"]["max"] is not None
            assert d["omega_history"]["stddev"] is not None
            assert d["decision_distribution"]["USE_MEMORY"] == 6
            assert d["domain_switching"]["primary"] == "general"
            assert len(d["call_frequency"]["hourly"]) == 24
            assert len(d["call_frequency"]["daily"]) == 7
        finally:
            _cleanup_outcomes(ids)


class TestBehavioralProfileCrossTenant:
    def test_cross_tenant_denied(self):
        """Tenant 2 cannot see tenant 1's agent profile data."""
        _agent_id = "bp_cross_tenant_agent"
        ids = _inject_outcomes(_agent_id, _KH_1, count=3)
        try:
            # Tenant 2 should get empty profile (agent belongs to tenant 1)
            r = client.get(f"/v1/agent/{_agent_id}/behavioral-profile", headers=AUTH_2)
            assert r.status_code == 200
            d = r.json()
            assert d["omega_history"]["samples"] == 0
            assert d["decision_distribution"]["USE_MEMORY"] == 0
        finally:
            _cleanup_outcomes(ids)


class TestBehavioralProfileFieldStructure:
    def test_response_field_structure(self):
        """Verify all required fields are present with correct types."""
        _agent_id = "bp_structure_agent"
        ids = _inject_outcomes(_agent_id, _KH_1, count=4, omega=30.0, action="WARN")
        try:
            r = client.get(f"/v1/agent/{_agent_id}/behavioral-profile", headers=AUTH_1)
            assert r.status_code == 200
            d = r.json()
            # Top-level fields
            assert "agent_id" in d
            assert "call_frequency" in d
            assert "action_escalation" in d
            assert "domain_switching" in d
            assert "decision_distribution" in d
            assert "omega_history" in d
            # call_frequency structure
            assert isinstance(d["call_frequency"]["hourly"], list)
            assert isinstance(d["call_frequency"]["daily"], list)
            # action_escalation structure
            assert "ratio" in d["action_escalation"]
            assert "trend" in d["action_escalation"]
            # domain_switching structure
            assert "primary" in d["domain_switching"]
            assert "distribution" in d["domain_switching"]
            assert isinstance(d["domain_switching"]["distribution"], dict)
            # decision_distribution — 4 values
            for key in ("USE_MEMORY", "WARN", "ASK_USER", "BLOCK"):
                assert key in d["decision_distribution"]
                assert isinstance(d["decision_distribution"][key], int)
            # omega_history structure
            assert "mean" in d["omega_history"]
            assert "stddev" in d["omega_history"]
            assert "max" in d["omega_history"]
            assert "samples" in d["omega_history"]
            assert isinstance(d["omega_history"]["samples"], int)
        finally:
            _cleanup_outcomes(ids)
