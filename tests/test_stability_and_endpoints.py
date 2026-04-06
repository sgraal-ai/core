"""Tests for decision stability, boundary explainer, grok comparison, propagation trace, forecast hook."""
from fastapi.testclient import TestClient


def _make_client():
    from api.main import app, verify_api_key
    app.dependency_overrides[verify_api_key] = lambda: {
        "customer_id": "cus_test", "tier": "test", "calls_this_month": 0, "key_hash": "testhash"
    }
    return TestClient(app), app, verify_api_key


MEMORY = [{"id": "e1", "content": "test", "type": "semantic",
           "timestamp_age_days": 5, "source_trust": 0.9,
           "source_conflict": 0.1, "downstream_count": 2}]


# --- TASK 1: Decision Stability ---

def test_stability_fields_present():
    """decision_stable, hysteresis_band, stability_window in preflight response."""
    client, app, vak = _make_client()
    try:
        resp = client.post("/v1/preflight", json={
            "memory_state": MEMORY, "action_type": "reversible", "domain": "general",
        }, headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        data = resp.json()
        assert "decision_stable" in data
        assert isinstance(data["decision_stable"], bool)
        assert "hysteresis_band" in data
        assert isinstance(data["hysteresis_band"], bool)
        assert "stability_window" in data
        assert data["stability_window"] in ("narrow", "wide", "clear")
    finally:
        app.dependency_overrides.pop(vak, None)


def test_stability_window_clear_for_low_omega():
    """Low omega (<20) should have stability_window=clear."""
    client, app, vak = _make_client()
    try:
        resp = client.post("/v1/preflight", json={
            "memory_state": [{"id": "e1", "content": "safe", "type": "semantic",
                              "timestamp_age_days": 1, "source_trust": 0.99,
                              "source_conflict": 0.01, "downstream_count": 1}],
            "action_type": "informational", "domain": "general",
        }, headers={"Authorization": "Bearer fake"})
        data = resp.json()
        # Very safe input should produce clear window
        if data["omega_mem_final"] < 20:
            assert data["stability_window"] == "clear"
            assert data["hysteresis_band"] is False
    finally:
        app.dependency_overrides.pop(vak, None)


# --- TASK 2: Boundary Explainer ---

def test_boundary_decision_field_present():
    """boundary_decision field always present in preflight response."""
    client, app, vak = _make_client()
    try:
        resp = client.post("/v1/preflight", json={
            "memory_state": MEMORY, "action_type": "reversible", "domain": "general",
        }, headers={"Authorization": "Bearer fake"})
        data = resp.json()
        assert "boundary_decision" in data
        assert isinstance(data["boundary_decision"], bool)
        # If in boundary, explanation should be present
        if data["boundary_decision"]:
            assert "boundary_explanation" in data
            assert isinstance(data["boundary_explanation"], list)
            assert "decision_confidence" in data
    finally:
        app.dependency_overrides.pop(vak, None)


# --- TASK 3: Grok Comparison ---

def test_grok_compare_aligned():
    """Aligned decisions → decisions_aligned=true."""
    client, app, vak = _make_client()
    try:
        resp = client.post("/v1/compare/grok", json={
            "sgraal_decision": "BLOCK", "grok_decision": "BLOCK",
            "omega": 75.0, "domain": "fintech",
        }, headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["decisions_aligned"] is True
        assert data["difference_reason"] == ""
    finally:
        app.dependency_overrides.pop(vak, None)


def test_grok_compare_misaligned():
    """Misaligned decisions → proper difference_reason and recommendation."""
    client, app, vak = _make_client()
    try:
        resp = client.post("/v1/compare/grok", json={
            "sgraal_decision": "BLOCK", "grok_decision": "USE_MEMORY",
            "omega": 72.0, "domain": "fintech",
        }, headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["decisions_aligned"] is False
        assert len(data["difference_reason"]) > 0
        assert data["recommendation"] == "trust_sgraal"
        assert data["formal_contradiction_present"] is True
    finally:
        app.dependency_overrides.pop(vak, None)


def test_grok_compare_boundary():
    """Boundary omega → recommendation=re_verify."""
    client, app, vak = _make_client()
    try:
        resp = client.post("/v1/compare/grok", json={
            "sgraal_decision": "WARN", "grok_decision": "USE_MEMORY",
            "omega": 45.0, "domain": "general",
        }, headers={"Authorization": "Bearer fake"})
        data = resp.json()
        assert data["recommendation"] == "re_verify"
    finally:
        app.dependency_overrides.pop(vak, None)


# --- TASK 4: Propagation Trace ---

def test_propagation_trace_low_risk():
    """Low downstream count → LOW cascade risk."""
    client, app, vak = _make_client()
    try:
        resp = client.post("/v1/propagation/trace", json={
            "agent_id": "agent-test",
            "memory_state": [{"id": "m1", "content": "test", "downstream_count": 1}],
            "domain": "general",
        }, headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["cascade_risk"] == "LOW"
        assert data["containment"] == "SUCCESS"
        assert data["affected_agents"] == 1
        assert "agent-test" in data["propagation_chain"]
    finally:
        app.dependency_overrides.pop(vak, None)


def test_propagation_trace_high_risk():
    """High downstream in medical domain → HIGH/CRITICAL cascade risk."""
    client, app, vak = _make_client()
    try:
        resp = client.post("/v1/propagation/trace", json={
            "agent_id": "agent-medical",
            "memory_state": [
                {"id": "m1", "content": "patient data", "downstream_count": 8},
                {"id": "m2", "content": "dosage info", "downstream_count": 12},
            ],
            "domain": "medical",
        }, headers={"Authorization": "Bearer fake"})
        data = resp.json()
        assert data["cascade_risk"] in ("HIGH", "CRITICAL")
        assert data["affected_agents"] == 20
        assert data["max_depth"] <= 5
    finally:
        app.dependency_overrides.pop(vak, None)


# --- TASK 5: Forecast Hook ---

def test_forecast_integrated_field_present():
    """forecast_integrated field always present in preflight response."""
    client, app, vak = _make_client()
    try:
        resp = client.post("/v1/preflight", json={
            "memory_state": MEMORY, "action_type": "reversible", "domain": "general",
        }, headers={"Authorization": "Bearer fake"})
        data = resp.json()
        assert "forecast_integrated" in data
        assert isinstance(data["forecast_integrated"], bool)
    finally:
        app.dependency_overrides.pop(vak, None)
