"""Test that GET /v1/approvals returns agent_id per row."""
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def test_approvals_include_agent_id():
    """Each approval in GET /v1/approvals includes agent_id field."""
    from api.main import app, verify_api_key, _approvals
    import time, uuid

    app.dependency_overrides[verify_api_key] = lambda: {
        "customer_id": "cus_test", "tier": "test", "calls_this_month": 0, "key_hash": "testhash"
    }

    # Insert a test approval with agent_id
    aid = str(uuid.uuid4())
    _approvals[aid] = {
        "id": aid, "preflight_id": "req-test", "status": "pending",
        "expires_at": time.time() + 3600, "reason": "test",
        "agent_id": "agent-fintech-trade",
    }

    try:
        client = TestClient(app)
        resp = client.get("/v1/approvals", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        approvals = resp.json().get("approvals", [])
        match = [a for a in approvals if a["id"] == aid]
        assert len(match) == 1
        assert "agent_id" in match[0]
        assert match[0]["agent_id"] == "agent-fintech-trade"
    finally:
        _approvals.pop(aid, None)
        app.dependency_overrides.pop(verify_api_key, None)
