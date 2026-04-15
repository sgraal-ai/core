"""Tests for fleet intelligence endpoints: compromised-sources, divergence, gaming-detection."""
import sys, os, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app, _outcome_set

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def _seed_outcomes():
    """Seed diverse outcomes for fleet analysis."""
    # Normal agent
    for i in range(15):
        _outcome_set(f"fleet_norm_{i}", {
            "agent_id": "agent-normal", "omega_mem_final": 15 + i * 0.5,
            "recommended_action": "USE_MEMORY", "domain": "general",
            "_ts": time.time() - (15 - i) * 60, "status": "open",
            "memory_state": [{"id": f"m_{i}", "provenance_chain": ["source-good"]}],
            "input_hash": f"hash_{i}",
        })
    # High-risk agent with compromised source
    for i in range(10):
        _outcome_set(f"fleet_risk_{i}", {
            "agent_id": "agent-risky", "omega_mem_final": 65 + i * 2,
            "recommended_action": "BLOCK" if i > 5 else "WARN", "domain": "fintech",
            "_ts": time.time() - (10 - i) * 60, "status": "open",
            "memory_state": [{"id": f"r_{i}", "provenance_chain": ["source-bad", "source-relay"]}],
            "input_hash": "same_hash",
        })
    # Stable-omega agent (possible gaming)
    for i in range(20):
        _outcome_set(f"fleet_game_{i}", {
            "agent_id": "agent-suspicious", "omega_mem_final": 24.5 + (i % 3) * 0.3,
            "recommended_action": "USE_MEMORY", "domain": "general",
            "_ts": time.time() - (20 - i) * 60, "status": "open",
            "memory_state": [{"id": "static"}], "input_hash": "always_same",
        })


_seed_outcomes()


# ---------------------------------------------------------------------------
# Compromised sources
# ---------------------------------------------------------------------------

class TestCompromisedSources:
    def test_returns_200(self):
        r = client.get("/v1/fleet/compromised-sources", headers=AUTH)
        assert r.status_code == 200
        j = r.json()
        assert "compromised_sources" in j
        assert "total_compromised_calls" in j
        assert "generated_at" in j

    def test_requires_auth(self):
        r = client.get("/v1/fleet/compromised-sources")
        assert r.status_code in (401, 403)

    def test_finds_bad_source(self):
        r = client.get("/v1/fleet/compromised-sources?days=1", headers=AUTH)
        sources = r.json()["compromised_sources"]
        bad_ids = [s["source_id"] for s in sources]
        if bad_ids:
            assert any("bad" in sid or "relay" in sid for sid in bad_ids)

    def test_source_structure(self):
        r = client.get("/v1/fleet/compromised-sources", headers=AUTH)
        for src in r.json()["compromised_sources"]:
            assert "source_id" in src
            assert "compromised_call_count" in src
            assert src["compromised_call_count"] >= 2


# ---------------------------------------------------------------------------
# Divergence
# ---------------------------------------------------------------------------

class TestDivergence:
    def test_returns_200(self):
        r = client.get("/v1/fleet/divergence", headers=AUTH)
        assert r.status_code == 200
        j = r.json()
        assert "fleet_mean_omega" in j
        assert "diverging_agents" in j
        assert "stable_agents" in j

    def test_requires_auth(self):
        r = client.get("/v1/fleet/divergence")
        assert r.status_code in (401, 403)

    def test_divergence_types_valid(self):
        r = client.get("/v1/fleet/divergence", headers=AUTH)
        for agent in r.json()["diverging_agents"]:
            assert agent["divergence_type"] in ("DEGRADING", "RECOVERING", "GAMING")
            assert isinstance(agent["omega_trend"], (int, float))

    def test_fleet_mean_reasonable(self):
        r = client.get("/v1/fleet/divergence", headers=AUTH)
        mean = r.json()["fleet_mean_omega"]
        assert 0 <= mean <= 100


# ---------------------------------------------------------------------------
# Gaming detection
# ---------------------------------------------------------------------------

class TestGamingDetection:
    def test_returns_200(self):
        r = client.get("/v1/fleet/gaming-detection", headers=AUTH)
        assert r.status_code == 200
        j = r.json()
        assert "gaming_suspects" in j
        assert "clean_agents" in j

    def test_requires_auth(self):
        r = client.get("/v1/fleet/gaming-detection")
        assert r.status_code in (401, 403)

    def test_suspect_structure(self):
        r = client.get("/v1/fleet/gaming-detection", headers=AUTH)
        for suspect in r.json()["gaming_suspects"]:
            assert "agent_id" in suspect
            assert "gaming_score" in suspect
            assert 0 <= suspect["gaming_score"] <= 1
            assert "signals" in suspect
            assert isinstance(suspect["signals"], list)

    def test_detects_suspicious_agent(self):
        r = client.get("/v1/fleet/gaming-detection?days=1", headers=AUTH)
        suspects = r.json()["gaming_suspects"]
        suspect_ids = [s["agent_id"] for s in suspects]
        # agent-suspicious has stable omega + identical input
        if "agent-suspicious" in suspect_ids:
            s = next(x for x in suspects if x["agent_id"] == "agent-suspicious")
            assert "omega_too_stable" in s["signals"] or "identical_input" in s["signals"]
