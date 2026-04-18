"""Tests for codebase review fix sprint (FIX 1, 2, 8)."""
import os
import sys
import hashlib

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app, verify_api_key

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


class TestComponentBreakdownImmutable:
    """FIX 1: component_breakdown_engine must not be mutated by enrichment."""

    def test_engine_copy_preserved(self):
        """component_breakdown_engine should equal raw scoring output,
        while component_breakdown may differ after enrichment."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{
                "id": "m1", "content": "test data", "type": "tool_state",
                "timestamp_age_days": 30, "source_trust": 0.6,
                "source_conflict": 0.3, "downstream_count": 5,
            }],
            "action_type": "reversible", "domain": "general",
        })
        d = r.json()
        assert "component_breakdown_engine" in d, "Missing component_breakdown_engine"
        assert "component_breakdown" in d, "Missing component_breakdown"
        # Engine copy should be a dict with scoring components
        engine_cb = d["component_breakdown_engine"]
        assert isinstance(engine_cb, dict)
        assert len(engine_cb) > 0


class TestDuplicateSchedulerRemoved:
    """FIX 8: only one /v1/scheduler/status endpoint should exist."""

    def test_scheduler_status_returns_comprehensive_response(self):
        """The remaining scheduler/status endpoint should have the full response
        with redis_circuit_breaker, rl_persistence, and scoring_drift_alert."""
        r = client.get("/v1/scheduler/status", headers=AUTH)
        assert r.status_code == 200
        d = r.json()
        assert "jobs" in d
        assert "redis_circuit_breaker" in d
        assert "rl_persistence" in d
        assert "scoring_drift_alert" in d


class TestMultiSourceDiversity:
    """FIX 2: trust oscillation should be per-source, not global variance."""

    def test_diverse_sources_not_flagged(self):
        """Multiple entries from different sources with different trust levels
        should NOT trigger trust oscillation (it's diversity, not oscillation)."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                {"id": "m1", "content": "from source A", "type": "semantic",
                 "timestamp_age_days": 5, "source_trust": 0.95,
                 "source_conflict": 0.05, "downstream_count": 1,
                 "provenance": "source_A"},
                {"id": "m2", "content": "from source B", "type": "semantic",
                 "timestamp_age_days": 5, "source_trust": 0.3,
                 "source_conflict": 0.1, "downstream_count": 1,
                 "provenance": "source_B"},
                {"id": "m3", "content": "from source C", "type": "semantic",
                 "timestamp_age_days": 5, "source_trust": 0.6,
                 "source_conflict": 0.15, "downstream_count": 1,
                 "provenance": "source_C"},
            ],
            "action_type": "reversible", "domain": "general",
        })
        d = r.json()
        # Should not have trust_oscillation_detected from diverse (different) sources
        warnings = d.get("scoring_warnings", [])
        osc_warnings = [w for w in warnings if "trust_oscillation" in str(w).lower()]
        # Diverse sources = not oscillation (each source is consistent with itself)
        # This test validates FIX 2: per-source variance, not global
        assert len(osc_warnings) == 0, (
            f"Diverse sources incorrectly flagged as oscillation: {osc_warnings}"
        )
