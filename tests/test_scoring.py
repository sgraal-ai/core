import sys
import os
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring_engine import compute, MemoryEntry

# Patch out external services before importing the app
with patch.dict(os.environ, {}, clear=False):
    from fastapi.testclient import TestClient
    from api.main import app, API_KEYS, verify_api_key, TIER_LIMITS

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def _fresh_entry(**overrides):
    defaults = {
        "id": "test_001",
        "content": "Test memory",
        "type": "preference",
        "timestamp_age_days": 1,
        "source_trust": 0.95,
        "source_conflict": 0.05,
        "downstream_count": 1,
    }
    defaults.update(overrides)
    return defaults


# --- Scoring engine unit tests ---


class TestScoringEngine:
    def test_fresh_data_returns_use_memory(self):
        entries = [
            MemoryEntry(
                id="mem_001",
                content="Fresh data",
                type="preference",
                timestamp_age_days=1,
                source_trust=0.95,
                source_conflict=0.05,
                downstream_count=1,
            )
        ]
        result = compute(entries, action_type="informational", domain="general")

        assert result.recommended_action == "USE_MEMORY"
        assert result.omega_mem_final < 25
        assert result.assurance_score > 0

    def test_stale_data_irreversible_fintech_returns_block(self):
        entries = [
            MemoryEntry(
                id="mem_002",
                content="Old stale data",
                type="tool_state",
                timestamp_age_days=94,
                source_trust=0.5,
                source_conflict=0.6,
                downstream_count=10,
            )
        ]
        result = compute(entries, action_type="irreversible", domain="fintech")

        assert result.recommended_action == "BLOCK"
        assert result.omega_mem_final >= 70

    def test_empty_entries_returns_use_memory(self):
        result = compute([], action_type="reversible", domain="general")

        assert result.recommended_action == "USE_MEMORY"
        assert result.omega_mem_final == 0
        assert result.assurance_score == 100

    def test_component_breakdown_has_all_keys(self):
        entries = [
            MemoryEntry(
                id="mem_003",
                content="Test",
                type="semantic",
                timestamp_age_days=10,
                source_trust=0.8,
                source_conflict=0.2,
                downstream_count=3,
            )
        ]
        result = compute(entries)

        expected_keys = {
            "s_freshness", "s_drift", "s_provenance", "s_propagation",
            "r_recall", "r_encode", "s_interference", "s_recovery",
        }
        assert set(result.component_breakdown.keys()) == expected_keys

    def test_omega_clamped_to_0_100(self):
        entries = [
            MemoryEntry(
                id="mem_004",
                content="Extreme",
                type="policy",
                timestamp_age_days=1000,
                source_trust=0.0,
                source_conflict=1.0,
                downstream_count=100,
            )
        ]
        result = compute(entries, action_type="destructive", domain="medical")

        assert 0 <= result.omega_mem_final <= 100


# --- API integration tests ---


class TestPreflightAPI:
    def test_fresh_data_returns_use_memory(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
            "action_type": "informational",
            "domain": "general",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["recommended_action"] == "USE_MEMORY"

    def test_stale_data_irreversible_fintech_returns_block(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry(
                timestamp_age_days=94,
                source_trust=0.5,
                source_conflict=0.6,
                downstream_count=10,
            )],
            "action_type": "irreversible",
            "domain": "fintech",
        }, headers=AUTH)

        assert resp.status_code == 200
        data = resp.json()
        assert data["recommended_action"] == "BLOCK"

    def test_empty_memory_state_returns_400(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [],
            "action_type": "reversible",
            "domain": "general",
        }, headers=AUTH)

        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_missing_required_fields_returns_422(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [{"id": "incomplete"}],
        }, headers=AUTH)

        assert resp.status_code == 422

    def test_missing_auth_returns_error(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        })

        assert resp.status_code in (401, 403)

    def test_invalid_api_key_returns_401(self):
        resp = client.post("/v1/preflight", json={
            "memory_state": [_fresh_entry()],
        }, headers={"Authorization": "Bearer invalid_key"})

        assert resp.status_code == 401


class TestRateLimiting:
    def test_free_tier_rate_limit_returns_429(self):
        """Simulate a key that has exhausted its free tier quota."""
        from api.main import verify_api_key as _verify

        def mock_verify():
            return {
                "customer_id": "cus_rate_limit_test",
                "tier": "free",
                "calls_this_month": 10_000,
                "key_hash": None,
            }

        app.dependency_overrides[verify_api_key] = mock_verify
        try:
            resp = client.post("/v1/preflight", json={
                "memory_state": [_fresh_entry()],
            })

            assert resp.status_code == 429
            assert "10,000" in resp.json()["detail"]
            assert "free" in resp.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_under_limit_passes(self):
        def mock_verify():
            return {
                "customer_id": "cus_under_limit",
                "tier": "free",
                "calls_this_month": 9_999,
                "key_hash": None,
            }

        app.dependency_overrides[verify_api_key] = mock_verify
        try:
            resp = client.post("/v1/preflight", json={
                "memory_state": [_fresh_entry()],
            })

            assert resp.status_code == 200
        finally:
            app.dependency_overrides.clear()
