"""Tests for #34 (key anomaly detection) and #31 (.well-known hardening).

#34: Stolen/cloned API key detection via per-key activity tracking.
#31: Research constants removed from public .well-known, moved to authenticated endpoint.
"""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app, _key_activity, _key_activity_lock, _safe_key_hash, _track_key_activity, API_KEYS
import hashlib

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}
_KH = hashlib.sha256(b"sg_test_key_001").hexdigest()


class TestKeyAnomalyDetection:
    def _clear_activity(self):
        with _key_activity_lock:
            _key_activity.pop(_KH, None)

    def test_key_activity_endpoint_returns_signals(self):
        """GET /v1/security/key-activity must return anomaly signal fields."""
        self._clear_activity()
        r = client.get("/v1/security/key-activity", headers=AUTH)
        assert r.status_code == 200
        d = r.json()
        assert "suspicious" in d
        assert "unique_ips" in d
        assert "calls_last_hour" in d
        assert "calls_last_minute" in d
        assert "avg_rpm" in d
        assert "key_hash_prefix" in d
        assert isinstance(d["suspicious"], bool)

    def test_multi_ip_triggers_suspicious_flag(self):
        """When 3+ unique IPs appear in the same hour, the key is flagged."""
        self._clear_activity()
        # Simulate calls from 4 different IPs
        for ip in ["1.2.3.4", "5.6.7.8", "9.10.11.12", "13.14.15.16"]:
            _track_key_activity(_KH, ip)
        result = _track_key_activity(_KH, "17.18.19.20")
        assert result["suspicious"] is True
        assert result["unique_ips"] >= 3
        assert "unique IPs" in (result["reason"] or "")
        self._clear_activity()

    def test_normal_usage_not_suspicious(self):
        """A single IP making a few calls should NOT be flagged."""
        self._clear_activity()
        for _ in range(5):
            result = _track_key_activity(_KH, "10.0.0.1")
        assert result["suspicious"] is False
        assert result["unique_ips"] == 1
        self._clear_activity()


class TestWellKnownHardened:
    def test_well_known_does_not_expose_research_constants(self):
        """#31: phase_constant, polytope_dimensions, decision_thresholds must
        NOT appear in the public .well-known/sgraal.json endpoint."""
        r = client.get("/.well-known/sgraal.json")
        assert r.status_code == 200
        d = r.json()
        # These MUST be absent from the public endpoint
        assert "phase_constant" not in d
        assert "polytope_dimensions" not in d
        assert "polytope_axes" not in d
        assert "decision_thresholds" not in d
        # These MUST still be present (service discovery)
        assert d["api_version"] == "v1"
        assert "capabilities" in d
        assert "endpoints" in d
        assert "distributions" in d

    def test_research_constants_requires_auth(self):
        """GET /v1/research/constants must require authentication."""
        # Without auth → 401/403
        r = client.get("/v1/research/constants")
        assert r.status_code in (401, 403)
        # With auth → 200 and includes the research constants
        r2 = client.get("/v1/research/constants", headers=AUTH)
        assert r2.status_code == 200
        d = r2.json()
        assert d["phase_constant"] == 0.033
        assert d["polytope_dimensions"] == 5
        assert "polytope_axes" in d
        assert "per_type_thresholds_research" in d
        assert d["correlation_rho"] == -0.54
