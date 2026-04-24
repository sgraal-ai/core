"""Tests for /v1/preflight/stream SSE endpoint."""
import os, json
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

_CLEAN = [
    {"id": "e1", "content": "Clean memory entry", "type": "semantic",
     "timestamp_age_days": 5, "source_trust": 0.9, "source_conflict": 0.05, "downstream_count": 1}
]


def _parse_sse(response_text: str) -> list[dict]:
    """Parse SSE text into list of event dicts."""
    events = []
    for line in response_text.split("\n"):
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


class TestSSEStreaming:
    def test_stream_returns_200(self):
        r = client.post("/v1/preflight/stream", headers=AUTH, json={
            "memory_state": _CLEAN, "action_type": "reversible", "domain": "general", "dry_run": True})
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")

    def test_stream_emits_multiple_events(self):
        """Stream must emit at least 3 intermediate events before the final complete."""
        r = client.post("/v1/preflight/stream", headers=AUTH, json={
            "memory_state": _CLEAN, "action_type": "reversible", "domain": "general", "dry_run": True})
        events = _parse_sse(r.text)
        assert len(events) >= 3, f"Expected 3+ events, got {len(events)}"

    def test_stream_has_module_and_detection_events(self):
        """Stream includes both module_complete and detection_complete events."""
        r = client.post("/v1/preflight/stream", headers=AUTH, json={
            "memory_state": _CLEAN, "action_type": "reversible", "domain": "general", "dry_run": True})
        events = _parse_sse(r.text)
        event_types = {e.get("event") for e in events}
        assert "module_complete" in event_types, "Missing module_complete events"
        assert "detection_complete" in event_types, "Missing detection_complete events"
        assert "complete" in event_types, "Missing final complete event"

    def test_stream_progress_increases(self):
        """Progress field should monotonically increase across events."""
        r = client.post("/v1/preflight/stream", headers=AUTH, json={
            "memory_state": _CLEAN, "action_type": "reversible", "domain": "general", "dry_run": True})
        events = _parse_sse(r.text)
        progresses = [e.get("progress", 0) for e in events if "progress" in e]
        assert len(progresses) >= 3
        for i in range(1, len(progresses)):
            assert progresses[i] >= progresses[i-1], f"Progress decreased: {progresses[i-1]} → {progresses[i]}"

    def test_stream_final_event_has_decision(self):
        """The final 'complete' event contains the decision and omega."""
        r = client.post("/v1/preflight/stream", headers=AUTH, json={
            "memory_state": _CLEAN, "action_type": "reversible", "domain": "general", "dry_run": True})
        events = _parse_sse(r.text)
        final = [e for e in events if e.get("event") == "complete"]
        assert len(final) == 1
        result = final[0].get("result", {})
        assert "recommended_action" in result
        assert "omega_mem_final" in result
        assert result["recommended_action"] in ("USE_MEMORY", "WARN", "ASK_USER", "BLOCK")

    def test_stream_includes_invariant_check(self):
        """Stream includes an invariant_check event."""
        r = client.post("/v1/preflight/stream", headers=AUTH, json={
            "memory_state": _CLEAN, "action_type": "reversible", "domain": "general", "dry_run": True})
        events = _parse_sse(r.text)
        inv_events = [e for e in events if e.get("event") == "invariant_check"]
        assert len(inv_events) == 1
        assert "result" in inv_events[0]
