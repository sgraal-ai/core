"""Tests for new features: headers, auto profile, adapt, .sgraal, SLA."""
import pytest


def _client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


AUTH = {"Authorization": "Bearer sg_demo_playground"}


def _entry(**kw):
    base = {"id": "m1", "content": "Standard data.", "type": "semantic",
            "timestamp_age_days": 5, "source_trust": 0.9,
            "source_conflict": 0.05, "downstream_count": 1}
    base.update(kw)
    return base


def _preflight(entries=None, action_type="informational", **extra):
    c = _client()
    payload = {"memory_state": entries or [_entry()],
               "domain": "general", "action_type": action_type}
    payload.update(extra)
    resp = c.post("/v1/preflight", json=payload, headers=AUTH)
    assert resp.status_code == 200
    return resp.json()


# ── Task 1: Preflight headers ──────────────────────────────────────────────

class TestPreflightHeaders:
    def test_preflight_headers_present(self):
        data = _preflight()
        h = data.get("_headers", {})
        assert "X-Sgraal-Decision" in h
        assert "X-Sgraal-Omega" in h
        assert "X-Sgraal-Assurance" in h

    def test_attack_surface_header(self):
        data = _preflight()
        h = data.get("_headers", {})
        assert "X-Sgraal-Attack-Surface" in h
        assert h["X-Sgraal-Attack-Surface"] in ("NONE", "LOW", "MODERATE", "HIGH", "CRITICAL")

    def test_naturalness_header(self):
        data = _preflight()
        h = data.get("_headers", {})
        assert "X-Sgraal-Naturalness" in h
        assert h["X-Sgraal-Naturalness"] in ("ORGANIC", "PLAUSIBLE", "SYNTHETIC", "FABRICATED")


# ── Task 2: Auto profile ───────────────────────────────────────────────────

class TestAutoProfile:
    def test_auto_profile_informational(self):
        data = _preflight(action_type="informational")
        assert data.get("auto_profile_selected") is True

    def test_auto_profile_destructive(self):
        data = _preflight(action_type="destructive")
        assert data.get("auto_profile_selected") is True
        assert data.get("response_profile_used") == "standard"

    def test_auto_profile_explicit(self):
        data = _preflight(action_type="informational", response_profile="standard")
        assert data.get("auto_profile_selected") is False


# ── Task 3: Adapt endpoint ────────────────────────────────────────────────

class TestAdaptEndpoint:
    def test_adapt_raw_strings(self):
        c = _client()
        resp = c.post("/v1/adapt", json={
            "data": ["fact one", "fact two", "fact three"],
            "provider": "auto"
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data["entry_count"] == 3
        assert data["provider_detected"] == "raw"
        assert data["ready_for_preflight"] is True
        assert len(data["memory_state"]) == 3

    def test_adapt_mem0_format(self):
        c = _client()
        resp = c.post("/v1/adapt", json={
            "data": [{"memory": "user likes coffee", "score": 0.92}],
            "provider": "auto"
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider_detected"] == "mem0"
        assert data["memory_state"][0]["source_trust"] == 0.92


# ── Task 4: .sgraal policy ────────────────────────────────────────────────

class TestSgraalPolicy:
    def test_policy_validate_valid_config(self):
        c = _client()
        resp = c.post("/v1/policy/validate", json={
            "config": {"version": "1.0", "agent_id": "test-agent", "domain": "general"}
        }, headers=AUTH)
        assert resp.status_code == 200
        assert resp.json()["valid"] is True
        assert resp.json()["errors"] == []

    def test_policy_validate_invalid_config(self):
        c = _client()
        resp = c.post("/v1/policy/validate", json={
            "config": {"version": "1.0"}
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert len(data["errors"]) >= 1


# ── Task 5: SLA endpoints ─────────────────────────────────────────────────

class TestSLAEndpoints:
    def test_sla_configure_endpoint(self):
        c = _client()
        resp = c.post("/v1/sla/configure", json={
            "domain": "fintech", "max_block_rate": 0.05
        }, headers=AUTH)
        assert resp.status_code == 200
        assert resp.json()["configured"] is True

    def test_sla_status_endpoint(self):
        c = _client()
        resp = c.get("/v1/sla/status?domain=general", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "block_rate" in data
        assert "sla_breaches" in data
