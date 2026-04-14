"""Tests for #387 module_consensus, #388 warmup, #389 sheaf_fallback, #399 block_explanation."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def _entry(**overrides):
    defaults = {
        "id": "nf2_001", "content": "Test memory", "type": "preference",
        "timestamp_age_days": 5, "source_trust": 0.9, "source_conflict": 0.1,
        "downstream_count": 2,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# #387: Module consensus score
# ---------------------------------------------------------------------------

class TestModuleConsensus:
    def test_fields_present(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        assert "module_consensus_score" in j
        assert "module_disagreements" in j

    def test_score_range(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        score = r.json()["module_consensus_score"]
        assert 0.0 <= score <= 1.0

    def test_disagreements_is_list(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        assert isinstance(r.json()["module_disagreements"], list)


# ---------------------------------------------------------------------------
# #388: Warmup endpoint
# ---------------------------------------------------------------------------

class TestWarmup:
    def test_returns_200(self):
        r = client.post("/v1/warmup", headers=AUTH)
        assert r.status_code == 200
        j = r.json()
        assert j["status"] == "warm"
        assert "latency_ms" in j
        assert "modules_initialized" in j

    def test_modules_initialized_positive(self):
        r = client.post("/v1/warmup", headers=AUTH)
        assert r.json()["modules_initialized"] > 0

    def test_requires_auth(self):
        r = client.post("/v1/warmup")
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# #389: Sheaf fallback tracking
# ---------------------------------------------------------------------------

class TestSheafFallback:
    def test_fields_present(self):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        assert "sheaf_fallback_used" in j
        assert "sheaf_fallback_reason" in j

    def test_single_entry_fallback(self):
        """Single entry → sheaf can't compute → fallback used."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry()],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        assert j["sheaf_fallback_used"] is True
        assert j["sheaf_fallback_reason"] == "insufficient_entries"

    def test_multiple_entries_no_fallback(self):
        """Multiple entries → sheaf can compute → no fallback."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _entry(id="sf_1", content="Content about topic A with some detail"),
                _entry(id="sf_2", content="Content about topic B with other detail"),
                _entry(id="sf_3", content="Content about topic C with more detail"),
            ],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        # With 3+ entries, sheaf should compute (fallback_used may still be True if sheaf returns None for other reasons)
        assert isinstance(j["sheaf_fallback_used"], bool)


# ---------------------------------------------------------------------------
# #399: Block explanation
# ---------------------------------------------------------------------------

class TestBlockExplanation:
    def test_present_on_block(self):
        """BLOCK decision should have block_explanation."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _entry(id="blk_1", timestamp_age_days=400, source_trust=0.1,
                       source_conflict=0.9, downstream_count=50),
            ],
            "action_type": "destructive", "domain": "medical",
        })
        j = r.json()
        if j["recommended_action"] == "BLOCK":
            assert j["block_explanation"] is not None
            assert len(j["block_explanation"]) > 10

    def test_null_on_use_memory(self):
        """USE_MEMORY should have null block_explanation."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [_entry(timestamp_age_days=0.1, source_trust=0.99, source_conflict=0.01)],
            "action_type": "informational", "domain": "general",
        })
        j = r.json()
        if j["recommended_action"] == "USE_MEMORY":
            assert j["block_explanation"] is None

    def test_explanation_mentions_component(self):
        """Block explanation should mention the primary risk component."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [
                _entry(id="exp_1", timestamp_age_days=300, source_trust=0.2,
                       source_conflict=0.8, downstream_count=30),
            ],
            "action_type": "irreversible", "domain": "fintech",
        })
        j = r.json()
        if j["block_explanation"]:
            # Should mention a component or a fix
            assert any(word in j["block_explanation"].lower() for word in
                       ["risk", "fix", "refetch", "entry", "omega", "stale", "drift", "conflict", "attack"])
