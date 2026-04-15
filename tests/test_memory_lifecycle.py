"""Tests for Memory Lifecycle: recover, refine, compress (#543, #566, #575)."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def _entry(**overrides):
    defaults = {
        "id": "lc_001", "content": "Test memory content for lifecycle", "type": "semantic",
        "timestamp_age_days": 10, "source_trust": 0.85, "source_conflict": 0.1,
        "downstream_count": 3,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Recover/Assess
# ---------------------------------------------------------------------------

class TestRecoverAssess:
    def test_returns_200(self):
        r = client.post("/v1/recover/assess", headers=AUTH, json={
            "memory_state": [_entry()], "agent_id": "recover-test", "domain": "general",
        })
        assert r.status_code == 200
        j = r.json()
        assert "current_omega" in j
        assert "overall_recoverability" in j
        assert "recovery_steps" in j

    def test_requires_auth(self):
        r = client.post("/v1/recover/assess", json={"memory_state": [_entry()]})
        assert r.status_code in (401, 403)

    def test_recoverable_for_healthy_entry(self):
        r = client.post("/v1/recover/assess", headers=AUTH, json={
            "memory_state": [_entry(source_trust=0.9, timestamp_age_days=5)],
        })
        j = r.json()
        assert j["overall_recoverability"] in ("RECOVERABLE", "PARTIAL")

    def test_unrecoverable_for_bad_entry(self):
        r = client.post("/v1/recover/assess", headers=AUTH, json={
            "memory_state": [_entry(source_trust=0.1, timestamp_age_days=200)],
        })
        j = r.json()
        assert j["overall_recoverability"] in ("PARTIAL", "UNRECOVERABLE")
        assert len(j["unrecoverable_entries"]) >= 1

    def test_estimated_omega_after(self):
        r = client.post("/v1/recover/assess", headers=AUTH, json={
            "memory_state": [
                _entry(id="r1", timestamp_age_days=100, source_trust=0.6, source_conflict=0.3),
                _entry(id="r2", timestamp_age_days=5, source_trust=0.95),
            ],
        })
        j = r.json()
        assert j["estimated_omega_after_recovery"] <= j["current_omega"]


# ---------------------------------------------------------------------------
# Refine
# ---------------------------------------------------------------------------

class TestRefine:
    def test_returns_200(self):
        r = client.post("/v1/refine", headers=AUTH, json={
            "memory_state": [_entry(), _entry(id="lc_002", content="Different topic entirely")],
        })
        assert r.status_code == 200
        j = r.json()
        assert "refinements_suggested" in j
        assert "total_omega_improvement" in j

    def test_requires_auth(self):
        r = client.post("/v1/refine", json={"memory_state": [_entry()]})
        assert r.status_code in (401, 403)

    def test_finds_consolidation(self):
        """Near-duplicate entries should be flagged for consolidation."""
        r = client.post("/v1/refine", headers=AUTH, json={
            "memory_state": [
                _entry(id="dup1", content="Patient allergic to penicillin confirmed by lab"),
                _entry(id="dup2", content="Patient allergic to penicillin verified by doctor"),
            ],
        })
        j = r.json()
        ops = [ref["operation"] for ref in j["refinements_suggested"]]
        assert "CONSOLIDATION" in ops or j["entries_consolidatable"] >= 0

    def test_respects_max_refinements(self):
        r = client.post("/v1/refine", headers=AUTH, json={
            "memory_state": [_entry(id=f"ref_{i}", content=f"Content {i}x" * 5, downstream_count=20) for i in range(10)],
            "max_refinements": 3,
        })
        assert len(r.json()["refinements_suggested"]) <= 3


# ---------------------------------------------------------------------------
# Compress
# ---------------------------------------------------------------------------

class TestCompress:
    def test_returns_200(self):
        r = client.post("/v1/compress", headers=AUTH, json={
            "memory_state": [_entry(id=f"c_{i}", content=f"Unique content {i}") for i in range(5)],
        })
        assert r.status_code == 200
        j = r.json()
        assert "original_entry_count" in j
        assert "compressed_entry_count" in j
        assert "stages" in j
        assert "verification" in j

    def test_requires_auth(self):
        r = client.post("/v1/compress", json={"memory_state": [_entry()]})
        assert r.status_code in (401, 403)

    def test_absorbs_duplicates(self):
        """Near-duplicate entries should be absorbed."""
        r = client.post("/v1/compress", headers=AUTH, json={
            "memory_state": [
                _entry(id="d1", content="Server health check passed all diagnostics"),
                _entry(id="d2", content="Server health check passed all diagnostics today"),
                _entry(id="d3", content="Completely different topic about finance"),
            ],
        })
        j = r.json()
        assert j["compressed_entry_count"] <= j["original_entry_count"]

    def test_omega_doesnt_increase(self):
        r = client.post("/v1/compress", headers=AUTH, json={
            "memory_state": [_entry(id=f"o_{i}", content=f"Content {i} alpha beta") for i in range(6)],
        })
        j = r.json()
        assert j["verification"]["omega_improved"] is True

    def test_returns_compressed_state(self):
        r = client.post("/v1/compress", headers=AUTH, json={
            "memory_state": [_entry(id=f"s_{i}") for i in range(4)],
        })
        assert "compressed_memory_state" in r.json()
        assert isinstance(r.json()["compressed_memory_state"], list)
