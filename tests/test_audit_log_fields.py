"""Tests that audit log GET response includes timestamp and omega fields."""
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def _make_client():
    from api.main import app, verify_api_key
    app.dependency_overrides[verify_api_key] = lambda: {
        "customer_id": "cus_test", "tier": "test", "calls_this_month": 0, "key_hash": "testhash"
    }
    return TestClient(app), app, verify_api_key


# Supabase returns "created_at" — API maps it to "timestamp" for dashboard
MOCK_ROWS = [
    {"created_at": "2026-04-06T12:00:00Z", "omega_mem_final": 42.5, "decision": "WARN",
     "agent_id": "agent-1", "domain": "fintech", "action_type": "irreversible",
     "request_id": "req-001", "api_key_id": "testhash", "event_type": "preflight"},
]


@patch("api.main.supabase_service_client")
def test_timestamp_field_present(mock_sb):
    """Audit log entries include timestamp field (from Supabase timestamp column)."""
    client, app, verify_api_key = _make_client()
    mock_result = MagicMock()
    mock_result.data = [dict(r) for r in MOCK_ROWS]
    mock_result.count = 1
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result
    try:
        resp = client.get("/v1/audit-log", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        entries = resp.json()["entries"]
        assert len(entries) == 1
        assert "timestamp" in entries[0]
        assert entries[0]["timestamp"] == "2026-04-06T12:00:00Z"
    finally:
        app.dependency_overrides.pop(verify_api_key, None)


@patch("api.main.supabase_service_client")
def test_omega_field_present(mock_sb):
    """Audit log entries include omega field mapped from omega_mem_final."""
    client, app, verify_api_key = _make_client()
    mock_result = MagicMock()
    mock_result.data = [dict(r) for r in MOCK_ROWS]
    mock_result.count = 1
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result
    try:
        resp = client.get("/v1/audit-log", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        entries = resp.json()["entries"]
        assert len(entries) == 1
        assert "omega" in entries[0]
        assert entries[0]["omega"] == 42.5
    finally:
        app.dependency_overrides.pop(verify_api_key, None)


