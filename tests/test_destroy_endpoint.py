"""Tests for POST /v1/destroy — the destroy pipeline."""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


class TestDestroyEndpoint:
    def test_destroy_returns_landauer_cost_and_merkle_root(self):
        r = client.post(
            "/v1/destroy",
            headers=AUTH,
            json={"agent_id": "agent_x", "entry_ids": ["e1", "e2", "e3"], "reason": "test"},
        )
        assert r.status_code == 200
        d = r.json()
        assert d["destroyed"] is True
        assert d["entry_count"] == 3
        assert d["landauer_cost_joules"] > 0
        assert d["landauer_cost_bits"] > 0
        assert len(d["merkle_root"]) == 64  # SHA-256 hex
        assert d["audit_id"]
        assert d["agent_id"] == "agent_x"
        assert d["reason"] == "test"

    def test_destroy_rejects_empty_entry_ids(self):
        r = client.post(
            "/v1/destroy",
            headers=AUTH,
            json={"agent_id": "agent_x", "entry_ids": [], "reason": "test"},
        )
        assert r.status_code == 400
        assert "non-empty" in r.json()["detail"]

    def test_destroy_rejects_oversized_batch(self):
        r = client.post(
            "/v1/destroy",
            headers=AUTH,
            json={
                "agent_id": "agent_x",
                "entry_ids": [f"e{i}" for i in range(1001)],
                "reason": "test",
            },
        )
        assert r.status_code == 400
        assert "1000" in r.json()["detail"]

    def test_destroy_requires_auth(self):
        r = client.post(
            "/v1/destroy",
            json={"agent_id": "agent_x", "entry_ids": ["e1"], "reason": "test"},
        )
        assert r.status_code in (401, 403)

    def test_destroy_landauer_cost_scales_with_entry_count(self):
        r1 = client.post(
            "/v1/destroy",
            headers=AUTH,
            json={"agent_id": "agent_x", "entry_ids": ["e1"], "reason": "test"},
        )
        r2 = client.post(
            "/v1/destroy",
            headers=AUTH,
            json={"agent_id": "agent_x", "entry_ids": ["e1", "e2", "e3", "e4", "e5"], "reason": "test"},
        )
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r2.json()["landauer_cost_joules"] > r1.json()["landauer_cost_joules"]
