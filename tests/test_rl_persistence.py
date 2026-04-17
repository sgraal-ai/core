"""Tests for RL Q-table Redis persistence across deploys.

The Q-table must survive process restarts via Redis. If Redis is unavailable,
learning continues in memory without crashing.
"""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from scoring_engine.rl_policy import QTable, ACTIONS


class TestRLPersistence:
    def test_qtable_persists_via_to_dict_from_dict(self):
        """Simulate a deploy restart: save Q-table to a dict (like Redis JSON),
        create a fresh QTable, load from the dict. Learning must survive."""
        # Train
        qt1 = QTable()
        qt1.update("fintech", "2:1:3:0", 3, reward=1.0)  # BLOCK gets +1
        qt1.update("fintech", "2:1:3:0", 0, reward=-1.0)  # USE_MEMORY gets -1
        qt1.update("fintech", "1:0:1:0", 2, reward=0.5)
        assert qt1.get_episodes("fintech") == 3
        q_before = qt1.get_q_values("fintech", "2:1:3:0")[:]

        # "Restart" — serialize, create fresh instance, deserialize
        snapshot = qt1.to_dict()
        qt2 = QTable()
        qt2.from_dict(snapshot)

        # Verify learning survived
        q_after = qt2.get_q_values("fintech", "2:1:3:0")
        assert q_after == q_before, f"Q-values changed across restart: {q_before} → {q_after}"
        assert qt2.get_episodes("fintech") == 3

        # Verify best action is consistent
        best_idx1, best_val1 = qt1.get_best_action("fintech", "2:1:3:0")
        best_idx2, best_val2 = qt2.get_best_action("fintech", "2:1:3:0")
        assert best_idx1 == best_idx2
        assert best_val1 == best_val2

    def test_redis_failure_falls_back_to_memory(self):
        """If Redis is unavailable, QTable must still work — learning
        happens in memory, updates don't crash, get_q_values returns
        the correct values."""
        qt = QTable()
        # Force Redis to be "unavailable" by setting the helpers to broken functions
        qt._redis_initialized = True
        qt._redis_get = None
        qt._redis_set = None

        # Learning must work without Redis
        qt.update("general", "0:0:0:0", 0, reward=1.0)
        qt.update("general", "0:0:0:0", 3, reward=-1.0)
        assert qt.get_episodes("general") == 2

        q = qt.get_q_values("general", "0:0:0:0")
        assert q[0] > 0, f"Q(USE_MEMORY) should be positive after +1 reward, got {q[0]}"
        assert q[3] < 0, f"Q(BLOCK) should be negative after -1 reward, got {q[3]}"

        # persistence_status should not crash
        status = qt.persistence_status()
        assert "general" in status
        assert status["general"]["episodes"] == 2
        assert status["general"]["loaded_from_redis"] is False

    def test_scheduler_status_shows_rl_persistence(self):
        """GET /v1/scheduler/status must include rl_persistence with
        per-domain episode counts and loaded_from_redis flags."""
        from api.main import app
        client = TestClient(app)
        AUTH = {"Authorization": "Bearer sg_test_key_001"}

        r = client.get("/v1/scheduler/status", headers=AUTH)
        assert r.status_code == 200
        d = r.json()
        assert "rl_persistence" in d, "rl_persistence missing from scheduler/status"
        rl = d["rl_persistence"]
        # Should have entries for all 6 domains
        for domain in ["general", "fintech", "medical", "legal", "coding", "customer_support"]:
            assert domain in rl, f"domain {domain} missing from rl_persistence"
            entry = rl[domain]
            assert "episodes" in entry
            assert "loaded_from_redis" in entry
            assert isinstance(entry["episodes"], int)
            assert isinstance(entry["loaded_from_redis"], bool)
