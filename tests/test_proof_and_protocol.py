"""Tests for proof-of-decision, court authority, passport TTL, and anti-consensus."""
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

PREFLIGHT_PAYLOAD = {
    "memory_state": MEMORY,
    "action_type": "reversible",
    "domain": "general",
}


# --- TASK 1: Proof-of-decision ---

def test_preflight_input_hash_present():
    """input_hash, deterministic, reproducible, proof_version in preflight response."""
    client, app, vak = _make_client()
    try:
        resp = client.post("/v1/preflight", json=PREFLIGHT_PAYLOAD, headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        data = resp.json()
        assert "input_hash" in data
        assert len(data["input_hash"]) == 64  # SHA256 hex
        assert data["deterministic"] is True
        assert data["reproducible"] is True
        assert data["proof_version"] == "v1"
    finally:
        app.dependency_overrides.pop(vak, None)


def test_preflight_same_input_same_hash():
    """Same input produces same input_hash."""
    client, app, vak = _make_client()
    try:
        r1 = client.post("/v1/preflight", json=PREFLIGHT_PAYLOAD, headers={"Authorization": "Bearer fake"})
        r2 = client.post("/v1/preflight", json=PREFLIGHT_PAYLOAD, headers={"Authorization": "Bearer fake"})
        assert r1.json()["input_hash"] == r2.json()["input_hash"]
    finally:
        app.dependency_overrides.pop(vak, None)


# --- TASK 2: Court arbitrate ---

def test_court_arbitrate_authority_fields():
    """Court arbitrate response contains overridable=false and authority=formal_verification."""
    client, app, vak = _make_client()
    try:
        resp = client.post("/v1/court/arbitrate", json={
            "entries": [
                {"id": "a", "content": "Fresh data", "source_trust": 0.95, "timestamp_age_days": 1},
                {"id": "b", "content": "Stale data", "source_trust": 0.4, "timestamp_age_days": 60},
            ],
            "domain": "general",
        }, headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["overridable"] is False
        assert data["authority"] == "formal_verification"
    finally:
        app.dependency_overrides.pop(vak, None)


# --- TASK 3: Passport TTL ---

def test_passport_ephemeral_ttl():
    """Ephemeral passport valid_until is ~5 minutes from now."""
    client, app, vak = _make_client()
    try:
        resp = client.post("/v1/memory/passport/export", json={
            "agent_id": "test-agent", "memory_state": MEMORY, "passport_type": "ephemeral",
        }, headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        data = resp.json()
        from datetime import datetime, timezone
        issued = datetime.fromisoformat(data["issued_at"].replace("Z", "+00:00"))
        valid = datetime.fromisoformat(data["valid_until"].replace("Z", "+00:00"))
        diff_minutes = (valid - issued).total_seconds() / 60
        assert 4 <= diff_minutes <= 6  # ~5 minutes
        assert data["propagation_limit"] == 3
        assert data["passport_type"] == "ephemeral"
    finally:
        app.dependency_overrides.pop(vak, None)


def test_passport_standard_ttl():
    """Standard passport valid_until is ~1 hour from now."""
    client, app, vak = _make_client()
    try:
        resp = client.post("/v1/memory/passport/export", json={
            "agent_id": "test-agent", "memory_state": MEMORY, "passport_type": "standard",
        }, headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        data = resp.json()
        from datetime import datetime
        issued = datetime.fromisoformat(data["issued_at"].replace("Z", "+00:00"))
        valid = datetime.fromisoformat(data["valid_until"].replace("Z", "+00:00"))
        diff_hours = (valid - issued).total_seconds() / 3600
        assert 0.9 <= diff_hours <= 1.1
    finally:
        app.dependency_overrides.pop(vak, None)


def test_passport_archival_ttl():
    """Archival passport valid_until is ~30 days from now."""
    client, app, vak = _make_client()
    try:
        resp = client.post("/v1/memory/passport/export", json={
            "agent_id": "test-agent", "memory_state": MEMORY, "passport_type": "archival",
        }, headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        data = resp.json()
        from datetime import datetime
        issued = datetime.fromisoformat(data["issued_at"].replace("Z", "+00:00"))
        valid = datetime.fromisoformat(data["valid_until"].replace("Z", "+00:00"))
        diff_days = (valid - issued).total_seconds() / 86400
        assert 29 <= diff_days <= 31
    finally:
        app.dependency_overrides.pop(vak, None)


# --- TASK 4: Anti-consensus ---

def test_cross_agent_correlated_detected():
    """Correlated agents (same trust + same content) → correlated_agents=true."""
    client, app, vak = _make_client()
    try:
        shared_memory = [{"id": "m1", "content": "same data", "source_trust": 0.85, "timestamp_age_days": 5}]
        resp = client.post("/v1/cross-agent-check", json={
            "agents": [
                {"agent_id": "agent-a", "memory_state": shared_memory},
                {"agent_id": "agent-b", "memory_state": shared_memory},
            ],
        }, headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["correlated_agents"] is True
        assert data["consensus_weight_reduction"] == 0.5
        assert data["anti_hallucination_applied"] is True
    finally:
        app.dependency_overrides.pop(vak, None)


def test_cross_agent_uncorrelated():
    """Different agents with different memory → correlated_agents=false."""
    client, app, vak = _make_client()
    try:
        resp = client.post("/v1/cross-agent-check", json={
            "agents": [
                {"agent_id": "agent-a", "memory_state": [{"id": "m1", "content": "data A", "source_trust": 0.9, "timestamp_age_days": 2}]},
                {"agent_id": "agent-b", "memory_state": [{"id": "m2", "content": "data B", "source_trust": 0.5, "timestamp_age_days": 20}]},
            ],
        }, headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["correlated_agents"] is False
        assert data["consensus_weight_reduction"] == 0.0
        assert data["anti_hallucination_applied"] is False
    finally:
        app.dependency_overrides.pop(vak, None)
