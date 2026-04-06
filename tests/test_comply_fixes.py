"""Tests for SIEM export omega field and EU AI Act Article 14 block count."""
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def _make_client():
    from api.main import app, verify_api_key
    app.dependency_overrides[verify_api_key] = lambda: {
        "customer_id": "cus_test", "tier": "test", "calls_this_month": 0, "key_hash": "testhash"
    }
    return TestClient(app), app, verify_api_key


MOCK_AUDIT_ROWS = [
    {"created_at": "2026-04-06T12:00:00Z", "omega_mem_final": 82.4, "decision": "BLOCK",
     "api_key_id": "testhash", "event_type": "preflight"},
    {"created_at": "2026-04-06T11:00:00Z", "omega_mem_final": 15.3, "decision": "USE_MEMORY",
     "api_key_id": "testhash", "event_type": "preflight"},
]


@patch("api.main.supabase_service_client")
def test_siem_splunk_omega_not_empty(mock_sb):
    """SIEM Splunk export lines include omega value (not empty)."""
    client, app, verify_api_key = _make_client()
    mock_result = MagicMock()
    mock_result.data = [dict(r) for r in MOCK_AUDIT_ROWS]
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result
    try:
        resp = client.get("/v1/audit-log/export?format=splunk",
            headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        data = resp.json()
        lines = data.get("data", [])
        assert len(lines) >= 1
        # First line should have omega=82.4 (not omega=)
        assert "omega=82.4" in lines[0]
        assert "omega= " not in lines[0]
        assert "omega=\n" not in lines[0]
    finally:
        app.dependency_overrides.pop(verify_api_key, None)


@patch("api.main.supabase_service_client")
def test_article_14_block_count_from_audit_log(mock_sb):
    """EU AI Act report Article 14 block_count reflects actual BLOCK decisions."""
    client, app, verify_api_key = _make_client()

    # Mock: total calls = 10, blocks = 3
    def mock_execute_factory(count_val):
        result = MagicMock()
        result.count = count_val
        result.data = []
        return result

    call_count = [0]
    def mock_execute():
        call_count[0] += 1
        # First call: total count, Second call: block count
        if call_count[0] <= 1:
            return mock_execute_factory(10)
        return mock_execute_factory(3)

    mock_chain = MagicMock()
    mock_chain.execute = mock_execute
    mock_chain.eq.return_value = mock_chain
    mock_sb.table.return_value.select.return_value.eq.return_value = mock_chain

    try:
        resp = client.get("/v1/compliance/eu-ai-act/report?force_refresh=true",
            headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["article_14_human_oversight"]["block_count"] == 3
        assert data["article_17_quality_management"]["total_calls"] == 10
        assert data["article_17_quality_management"]["block_rate"] > 0
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
