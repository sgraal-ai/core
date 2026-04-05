"""Test that audit_log write does not include feature_flags column."""
from unittest.mock import patch, MagicMock


def test_audit_log_no_feature_flags():
    """Audit log record must not contain feature_flags (column doesn't exist in Supabase)."""
    from api.main import _audit_log

    mock_sb = MagicMock()
    captured = {}

    def capture_insert(record):
        captured.update(record)
        result = MagicMock()
        result.execute.return_value = None
        return result

    mock_sb.table.return_value.insert.side_effect = capture_insert

    with patch("api.main.supabase_service_client", mock_sb):
        _audit_log(
            "preflight", "req-123",
            {"key_hash": "abc"},
            "USE_MEMORY", 15.0,
            {"agent_id": "agent-1", "domain": "general", "action_type": "reversible"},
        )

    assert "feature_flags" not in captured
    assert captured["agent_id"] == "agent-1"
    assert captured["domain"] == "general"
    assert captured["action_type"] == "reversible"
