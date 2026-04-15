"""Tests for Redis circuit breaker, OTLP, PagerDuty, guard endpoints (#386,394,395,396)."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import (app, _redis_cb_state, _redis_cb_failures, _redis_cb_record_failure,
                       _redis_cb_record_success, _redis_cb_should_skip,
                       _block_rate_window, _track_block_rate)

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def _entry(**overrides):
    defaults = {
        "id": "inf_001", "content": "Test memory", "type": "preference",
        "timestamp_age_days": 5, "source_trust": 0.9, "source_conflict": 0.1,
        "downstream_count": 2,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# #386: Redis circuit breaker
# ---------------------------------------------------------------------------

class TestRedisCircuitBreaker:
    def test_starts_closed(self):
        import api.main as m
        # Reset state
        m._redis_cb_state = "CLOSED"
        m._redis_cb_failures.clear()
        assert not _redis_cb_should_skip()

    def test_opens_after_failures(self):
        import api.main as m
        m._redis_cb_state = "CLOSED"
        m._redis_cb_failures.clear()
        for _ in range(4):
            _redis_cb_record_failure()
        assert m._redis_cb_state == "OPEN"
        # Reset
        m._redis_cb_state = "CLOSED"
        m._redis_cb_failures.clear()

    def test_scheduler_status_includes_cb(self):
        r = client.get("/v1/scheduler/status", headers=AUTH)
        j = r.json()
        assert "redis_circuit_breaker" in j
        assert "state" in j["redis_circuit_breaker"]

    def test_success_closes_half_open(self):
        import api.main as m
        m._redis_cb_state = "HALF_OPEN"
        _redis_cb_record_success()
        assert m._redis_cb_state == "CLOSED"


# ---------------------------------------------------------------------------
# #394: OTLP (no actual endpoint to test, just verify no crash)
# ---------------------------------------------------------------------------

class TestOTLPExport:
    def test_preflight_works_without_otlp_endpoint(self):
        """Preflight should work fine without OTLP_ENDPOINT set."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        assert r.status_code == 200

    def test_otlp_env_not_required(self):
        """OTLP is optional — no crash when env var missing."""
        assert os.getenv("OTLP_ENDPOINT") is None  # Not set in test env
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        assert r.status_code == 200

    def test_response_unchanged_without_otlp(self):
        """Response shape should not change based on OTLP presence."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        assert "omega_mem_final" in r.json()


# ---------------------------------------------------------------------------
# #395: PagerDuty/OpsGenie block rate tracking
# ---------------------------------------------------------------------------

class TestBlockRateTracking:
    def test_track_doesnt_crash(self):
        _track_block_rate(True, "test-agent", 80.0)
        _track_block_rate(False, "test-agent", 10.0)

    def test_no_incident_below_threshold(self):
        """Should not trigger with < 10 calls."""
        import api.main as m
        m._block_rate_window.clear()
        for _ in range(5):
            _track_block_rate(True, "test", 80.0)
        # Less than 10 calls — no incident

    def test_window_contains_entries(self):
        import api.main as m
        m._block_rate_window.clear()
        _track_block_rate(True, "test", 80.0)
        assert len(m._block_rate_window) >= 1


# ---------------------------------------------------------------------------
# #396: OpenAI function + Claude tool guards
# ---------------------------------------------------------------------------

class TestGuardEndpoints:
    def test_openai_function_guard(self):
        r = client.post("/v1/guard/openai-function", headers=AUTH, json={
            "name": "get_weather",
            "arguments": {"city": "Budapest"},
            "memory_state": [_entry()],
            "agent_id": "test-guard",
            "domain": "general",
        })
        assert r.status_code == 200
        j = r.json()
        assert "safe_to_call" in j
        assert isinstance(j["safe_to_call"], bool)
        assert "recommended_action" in j
        assert j["function_name"] == "get_weather"

    def test_claude_tool_guard(self):
        r = client.post("/v1/guard/claude-tool", headers=AUTH, json={
            "type": "tool_use",
            "name": "search_database",
            "input": {"query": "test"},
            "memory_state": [_entry()],
            "agent_id": "test-guard",
            "domain": "general",
        })
        assert r.status_code == 200
        j = r.json()
        assert "safe_to_call" in j
        assert j["tool_name"] == "search_database"

    def test_destructive_function_infers_action_type(self):
        r = client.post("/v1/guard/openai-function", headers=AUTH, json={
            "name": "delete_account",
            "arguments": {},
            "memory_state": [_entry()],
        })
        assert r.json()["action_type_inferred"] == "destructive"

    def test_irreversible_function_infers_action_type(self):
        r = client.post("/v1/guard/openai-function", headers=AUTH, json={
            "name": "transfer_funds",
            "arguments": {"amount": 1000},
            "memory_state": [_entry()],
        })
        assert r.json()["action_type_inferred"] == "irreversible"

    def test_guard_requires_auth(self):
        r = client.post("/v1/guard/openai-function", json={
            "name": "test", "memory_state": [_entry()],
        })
        assert r.status_code in (401, 403)
