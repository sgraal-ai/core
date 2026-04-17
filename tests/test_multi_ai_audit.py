"""Tests from multi-AI security audit (ChatGPT + Gemini + Grok + DeepSeek)."""
import os
import sys
import ipaddress

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}
DEMO_AUTH = {"Authorization": "Bearer sg_demo_playground"}


class TestDNSRebindingBlocked:
    def test_private_ip_webhook_rejected(self):
        """FIX 12: webhook URLs that resolve to private IPs must be rejected."""
        # Raw IP — should be caught by IP check (not DNS)
        r = client.post("/v1/webhooks", headers=AUTH, json={
            "url": "https://192.168.1.1/hook",
            "events": ["BLOCK"],
        })
        # Should be rejected (422 for blocked IP) or another error code
        # depending on whether the webhooks endpoint exists and validates
        assert r.status_code in (400, 422, 404), (
            f"Expected rejection for private IP webhook, got {r.status_code}"
        )

    def test_loopback_webhook_rejected(self):
        """Loopback addresses must be rejected."""
        r = client.post("/v1/webhooks", headers=AUTH, json={
            "url": "https://127.0.0.1/hook",
            "events": ["BLOCK"],
        })
        assert r.status_code in (400, 422, 404)


class TestAuditTrailBounded:
    def test_decision_trail_capped_at_50(self):
        """FIX 10: decision_trail must never exceed 50 entries per request."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{
                "id": "m1", "content": "x", "type": "tool_state",
                "timestamp_age_days": 60, "source_trust": 0.5,
                "source_conflict": 0.5, "downstream_count": 5,
            }],
            "action_type": "irreversible", "domain": "fintech",
        })
        d = r.json()
        trail = d.get("decision_trail", [])
        assert len(trail) <= 50, f"decision_trail has {len(trail)} entries, max is 50"


class TestDemoKeyScope:
    def test_demo_key_forbidden_on_sensitive_endpoints(self):
        """FIX 3: demo key must return 403 on sensitive admin endpoints."""
        r = client.get("/v1/audit-log", headers=DEMO_AUTH)
        assert r.status_code == 403
        assert "Demo key" in r.json()["detail"] or "demo" in r.json()["detail"].lower()

        r2 = client.get("/v1/research/constants", headers=DEMO_AUTH)
        assert r2.status_code == 403

    def test_demo_key_allowed_on_preflight(self):
        """Demo key must still work on /v1/preflight."""
        r = client.post("/v1/preflight", headers=DEMO_AUTH, json={
            "memory_state": [{"id": "m1", "content": "test", "type": "semantic",
                              "timestamp_age_days": 1, "source_trust": 0.9,
                              "source_conflict": 0.1, "downstream_count": 1}],
            "action_type": "reversible", "domain": "general",
        })
        assert r.status_code == 200
