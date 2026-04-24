"""Tests for POST /v1/recover."""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from fastapi.testclient import TestClient
from api.main import app, _outcomes, _outcomes_lock
import hashlib

client = TestClient(app)
AUTH_1 = {"Authorization": "Bearer sg_test_key_001"}
AUTH_2 = {"Authorization": "Bearer sg_test_key_002"}

_KH_1 = hashlib.sha256("sg_test_key_001".encode()).hexdigest()
_KH_2 = hashlib.sha256("sg_test_key_002".encode()).hexdigest()


def _inject_agent_outcome(agent_id: str, key_hash: str):
    """Inject a synthetic outcome with memory_state for recovery testing."""
    import uuid
    oid = f"recover_test_{uuid.uuid4().hex[:8]}"
    with _outcomes_lock:
        _outcomes[oid] = {
            "request_id": oid,
            "agent_id": agent_id,
            "key_hash": key_hash,
            "domain": "general",
            "recommended_action": "WARN",
            "omega_mem_final": 45.0,
            "action_type": "reversible",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "open",
            "memory_state": [
                {"id": "m1", "content": "Old data from last year", "type": "semantic",
                 "timestamp_age_days": 200, "source_trust": 0.3, "source_conflict": 0.5,
                 "downstream_count": 2},
                {"id": "m2", "content": "Recent config", "type": "tool_state",
                 "timestamp_age_days": 1, "source_trust": 0.95, "source_conflict": 0.05,
                 "downstream_count": 0},
                {"id": "m3", "content": "User preference from months ago", "type": "preference",
                 "timestamp_age_days": 100, "source_trust": 0.4, "source_conflict": 0.3,
                 "downstream_count": 1},
            ],
        }
    return oid


def _cleanup(oid: str):
    with _outcomes_lock:
        _outcomes.pop(oid, None)


class TestRecoverDryRun:
    def test_dry_run_returns_plan(self):
        """commit=False should return planned actions without executing."""
        _agent_id = "recover_dry_agent"
        oid = _inject_agent_outcome(_agent_id, _KH_1)
        try:
            r = client.post("/v1/recover", headers=AUTH_1, json={
                "agent_id": _agent_id,
                "target_omega": 30,
                "commit": False,
            })
            assert r.status_code == 200
            d = r.json()
            assert d["status"] == "dry_run"
            assert d["agent_id"] == _agent_id
            assert "current_omega" in d
            assert "projected_omega" in d
            assert "planned_actions" in d
            assert isinstance(d["planned_actions"], list)
        finally:
            _cleanup(oid)


class TestRecoverCommit:
    def test_commit_executes_actions(self):
        """commit=True should execute recovery actions and return results."""
        _agent_id = "recover_commit_agent"
        oid = _inject_agent_outcome(_agent_id, _KH_1)
        try:
            r = client.post("/v1/recover", headers=AUTH_1, json={
                "agent_id": _agent_id,
                "target_omega": 20,
                "commit": True,
            })
            assert r.status_code == 200
            d = r.json()
            assert d["status"] == "committed"
            assert d["agent_id"] == _agent_id
            assert "request_id" in d
            assert "actions_taken" in d
            assert isinstance(d["actions_taken"], list)
            assert "current_omega" in d
            assert "projected_omega" in d
        finally:
            _cleanup(oid)


class TestRecoverCrossTenant:
    def test_cross_tenant_no_data(self):
        """Tenant 2 cannot recover tenant 1's agent data."""
        _agent_id = "recover_cross_tenant_agent"
        oid = _inject_agent_outcome(_agent_id, _KH_1)
        try:
            r = client.post("/v1/recover", headers=AUTH_2, json={
                "agent_id": _agent_id,
                "commit": False,
            })
            assert r.status_code == 200
            d = r.json()
            assert d["status"] == "no_data"
        finally:
            _cleanup(oid)


class TestRecoverAuditLog:
    def test_commit_has_request_id(self):
        """Committed recovery should have a request_id for audit trail."""
        _agent_id = "recover_audit_agent"
        oid = _inject_agent_outcome(_agent_id, _KH_1)
        try:
            r = client.post("/v1/recover", headers=AUTH_1, json={
                "agent_id": _agent_id,
                "commit": True,
            })
            assert r.status_code == 200
            d = r.json()
            assert d["status"] == "committed"
            assert "request_id" in d
            assert len(d["request_id"]) > 0
        finally:
            _cleanup(oid)


class TestRecoverAssessBackwardCompat:
    def test_assess_still_works(self):
        """POST /v1/recover/assess should still work unchanged."""
        r = client.post("/v1/recover/assess", headers=AUTH_1, json={
            "memory_state": [
                {"id": "bc1", "content": "Some old data", "type": "semantic",
                 "timestamp_age_days": 100, "source_trust": 0.4, "source_conflict": 0.3},
                {"id": "bc2", "content": "Recent data", "type": "tool_state",
                 "timestamp_age_days": 1, "source_trust": 0.95, "source_conflict": 0.05},
            ],
            "agent_id": "compat_agent",
            "domain": "general",
        })
        assert r.status_code == 200
        d = r.json()
        assert "current_omega" in d
        assert "overall_recoverability" in d
        assert "recovery_steps" in d
        assert d["agent_id"] == "compat_agent"
