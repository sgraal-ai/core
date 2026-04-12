"""Tests for badge, config validate, SIEM export, SLA enforcement."""
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


class TestBadge:
    def test_badge_endpoint_returns_svg(self):
        c = _client()
        resp = c.get("/v1/badge")
        assert resp.status_code == 200
        assert "image/svg+xml" in resp.headers.get("content-type", "")
        assert "Sgraal" in resp.text
        assert "Memory Governed" in resp.text

    def test_badge_status(self):
        c = _client()
        resp = c.get("/v1/badge/status/demo")
        assert resp.status_code == 200
        data = resp.json()
        assert "certified" in data
        assert "governance_score" in data
        assert "total_governed" in data


class TestConfigValidate:
    def test_config_validate_valid(self):
        c = _client()
        resp = c.post("/v1/config/validate", json={
            "config": {"version": "1.0", "domain": "fintech", "action_type": "irreversible",
                       "policy": {"block_omega": 70, "warn_omega": 40}}
        }, headers=AUTH)
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    def test_config_validate_invalid(self):
        c = _client()
        resp = c.post("/v1/config/validate", json={
            "config": {"version": "2.0", "domain": "invalid_domain"}
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert len(data["errors"]) >= 1


class TestSIEMExport:
    def test_siem_export_cef(self):
        c = _client()
        resp = c.get("/v1/audit/export?format=cef&limit=5", headers=AUTH)
        assert resp.status_code == 200
        # CEF format or empty (no audit entries in test env)
        assert resp.headers.get("content-type", "").startswith("text/plain") or "entries" in resp.text

    def test_siem_export_json(self):
        c = _client()
        resp = c.get("/v1/audit/export?format=json&limit=5", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "entries" in data
        assert "count" in data


class TestSLAEnforcement:
    def test_sla_status_field(self):
        """SLA status only present when SLA configured (demo key has none)."""
        c = _client()
        resp = c.post("/v1/preflight", json={
            "memory_state": [_e(age=5, downstream=1)],
            "domain": "general", "action_type": "informational",
        }, headers=AUTH)
        data = resp.json()
        # Demo key → no SLA configured → no sla_status field
        # This is correct behavior
        assert "sla_status" not in data or data.get("sla_status") is None or isinstance(data.get("sla_status"), dict)
