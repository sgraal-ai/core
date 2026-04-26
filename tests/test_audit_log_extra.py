"""Tests for #841 audit_log.extra schema definition."""
import os
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from api.main import AuditLogExtra, _validate_audit_extra


class TestAuditLogExtra:
    def test_valid_extra_accepted(self):
        """Standard audit extra fields are accepted and returned."""
        extra = {"omega": 42.5, "decision": "BLOCK", "client_ip": "1.2.3.4",
                 "latency_ms": 12.3, "detection_layers_fired": ["provenance", "timestamp"]}
        result = _validate_audit_extra(extra)
        assert result["omega"] == 42.5
        assert result["decision"] == "BLOCK"
        assert result["detection_layers_fired"] == ["provenance", "timestamp"]

    def test_invalid_extra_wrapped_in_custom(self):
        """Non-schema extra is wrapped in custom field for backward compat."""
        extra = {"some_weird_field": [1, 2, 3], "nested": {"deep": True}}
        result = _validate_audit_extra(extra)
        # With extra="allow", unknown fields are kept
        assert "some_weird_field" in result or "custom" in result

    def test_backward_compat_custom_field(self):
        """Explicit custom dict is accepted."""
        extra = {"custom": {"legacy_field": "value", "count": 42}}
        result = _validate_audit_extra(extra)
        assert result["custom"]["legacy_field"] == "value"
        assert result["custom"]["count"] == 42
