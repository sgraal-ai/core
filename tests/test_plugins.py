"""Tests for the registry-only plugin system."""
import os
import sys
import time

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from api.main import app
from plugins import SgraalPlugin, registry

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

_HEALTHY_MEM = [{
    "id": "m1",
    "content": "Fresh preference",
    "type": "preference",
    "timestamp_age_days": 1,
    "source_trust": 0.95,
    "source_conflict": 0.05,
    "downstream_count": 1,
}]


@pytest.fixture(autouse=True)
def deactivate_examples():
    """Ensure bundled example plugins are inactive for each test."""
    registry.deactivate("custom_freshness")
    registry.deactivate("domain_blocker")
    yield
    registry.deactivate("custom_freshness")
    registry.deactivate("domain_blocker")
    # Remove any test-only plugins
    for name in list(p["name"] for p in registry.list_plugins()):
        if name.startswith("test_"):
            registry.unregister(name)


class TestPluginSystem:
    def test_register_and_list_plugin(self):
        # Both bundled example plugins should be pre-installed
        r = client.get("/v1/plugins", headers=AUTH)
        assert r.status_code == 200
        names = [p["name"] for p in r.json()["plugins"]]
        assert "custom_freshness" in names
        assert "domain_blocker" in names

        # None should be active after fixture teardown
        for p in r.json()["plugins"]:
            if p["name"] in ("custom_freshness", "domain_blocker"):
                assert p["active"] is False

        # Activate custom_freshness
        r2 = client.post("/v1/plugins/activate", headers=AUTH, json={"name": "custom_freshness"})
        assert r2.status_code == 200
        assert r2.json()["activated"] is True

        r3 = client.get("/v1/plugins", headers=AUTH)
        active = [p for p in r3.json()["plugins"] if p["name"] == "custom_freshness"]
        assert active and active[0]["active"] is True

    def test_plugin_modifies_component_score(self):
        # Activate custom_freshness (discounts s_freshness by 10%)
        client.post("/v1/plugins/activate", headers=AUTH, json={"name": "custom_freshness"})

        # Use a somewhat-stale memory so s_freshness > 0
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{
                "id": "m1", "content": "Stale tool state",
                "type": "tool_state", "timestamp_age_days": 20,
                "source_trust": 0.8, "source_conflict": 0.2, "downstream_count": 2,
            }],
            "action_type": "reversible", "domain": "general",
        })
        assert r.status_code == 200
        d = r.json()
        assert "plugin_results" in d
        component_events = [e for e in d["plugin_results"]
                            if e["plugin"] == "custom_freshness" and e["hook"] == "on_component_score"]
        # Plugin was invoked on the s_freshness component and modified it
        assert len(component_events) >= 1
        modified_events = [e for e in component_events if e.get("modified")]
        assert len(modified_events) >= 1
        # Delta should be negative (discount)
        assert modified_events[0]["delta"] < 0

    def test_plugin_failure_does_not_crash_preflight(self):
        class BrokenPlugin(SgraalPlugin):
            name = "test_broken_plugin"
            version = "0.0.0"

            def on_component_score(self, component_name, score, memory_state):
                raise RuntimeError("intentional failure for test")

        registry.register(BrokenPlugin(), activate=True)

        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _HEALTHY_MEM,
            "action_type": "reversible",
            "domain": "general",
        })
        # Preflight must succeed despite broken plugin
        assert r.status_code == 200
        d = r.json()
        assert "omega_mem_final" in d
        # Plugin error should be captured in plugin_results
        assert "plugin_results" in d
        broken_events = [e for e in d["plugin_results"] if e["plugin"] == "test_broken_plugin"]
        assert len(broken_events) >= 1
        assert any("error" in e and "RuntimeError" in e["error"] for e in broken_events)

    def test_plugin_execution_time_limit_enforced(self):
        class SlowPlugin(SgraalPlugin):
            name = "test_slow_plugin"
            version = "0.0.0"

            def on_preflight_start(self, memory_state, context):
                time.sleep(0.025)  # 25ms — exceeds 10ms budget

        registry.register(SlowPlugin(), activate=True)

        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _HEALTHY_MEM,
            "action_type": "reversible",
            "domain": "general",
        })
        assert r.status_code == 200
        d = r.json()
        assert "plugin_results" in d
        slow_events = [e for e in d["plugin_results"] if e["plugin"] == "test_slow_plugin"]
        assert len(slow_events) >= 1
        # Duration should have been measured and exceed the budget
        assert slow_events[0]["duration_ms"] >= 10.0
        # And the error field should flag budget_exceeded
        assert any("budget_exceeded" in (e.get("error") or "") for e in slow_events)

    def test_unregister_plugin(self):
        class TemporaryPlugin(SgraalPlugin):
            name = "test_temp_plugin"
            version = "0.0.0"

        registry.register(TemporaryPlugin(), activate=False)

        # GET confirms it's installed
        r = client.get("/v1/plugins/test_temp_plugin", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["name"] == "test_temp_plugin"

        # DELETE it
        r2 = client.delete("/v1/plugins/test_temp_plugin", headers=AUTH)
        assert r2.status_code == 200
        assert r2.json()["unregistered"] is True

        # GET now 404s
        r3 = client.get("/v1/plugins/test_temp_plugin", headers=AUTH)
        assert r3.status_code == 404

        # DELETE again returns 404 (already gone)
        r4 = client.delete("/v1/plugins/test_temp_plugin", headers=AUTH)
        assert r4.status_code == 404

    def test_register_endpoint_rejects_code_upload(self):
        """The /v1/plugins/register endpoint MUST reject arbitrary code upload."""
        r = client.post("/v1/plugins/register", headers=AUTH, json={
            "name": "attacker",
            "code": "import os; os.system('rm -rf /')",
        })
        assert r.status_code == 410
        assert "activate" in r.json()["detail"].lower()

    def test_activate_nonexistent_plugin_returns_404(self):
        r = client.post("/v1/plugins/activate", headers=AUTH, json={"name": "does_not_exist"})
        assert r.status_code == 404
        assert "not installed" in r.json()["detail"].lower()

    def test_domain_blocker_plugin_overrides_decision(self):
        """Integration test: the bundled domain_blocker plugin forces BLOCK for 'medical'."""
        client.post("/v1/plugins/activate", headers=AUTH, json={"name": "domain_blocker"})

        # Call with medical domain — should be forced BLOCK regardless of memory quality
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _HEALTHY_MEM,
            "action_type": "reversible",
            "domain": "medical",
        })
        assert r.status_code == 200
        d = r.json()
        assert d["recommended_action"] == "BLOCK"
        # Non-medical domain should NOT be forced
        r2 = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": _HEALTHY_MEM,
            "action_type": "reversible",
            "domain": "general",
        })
        assert r2.status_code == 200
        # general + healthy memory should be USE_MEMORY or WARN, not BLOCK
        assert r2.json()["recommended_action"] in ("USE_MEMORY", "WARN")
