"""Tests for /v1/fleet/health-phase endpoint."""
import os
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


class TestFleetHealthPhase:
    def test_super_critical_all_fresh(self):
        """All fresh entries → super_critical phase."""
        entries = [{"id": f"e{i}", "content": "fresh", "type": "semantic",
                    "timestamp_age_days": 1, "source_trust": 0.9} for i in range(10)]
        r = client.post("/v1/fleet/health-phase", headers=AUTH, json={"entries": entries, "domain": "general"})
        assert r.status_code == 200
        j = r.json()
        assert j["phase"] == "super_critical"
        assert j["current_ratio"] == 1.0
        assert j["margin"] > 0

    def test_sub_critical_all_stale(self):
        """All stale entries → sub_critical phase."""
        entries = [{"id": f"e{i}", "content": "stale", "type": "semantic",
                    "timestamp_age_days": 500, "source_trust": 0.9} for i in range(10)]
        r = client.post("/v1/fleet/health-phase", headers=AUTH, json={"entries": entries, "domain": "general"})
        assert r.status_code == 200
        j = r.json()
        assert j["phase"] == "sub_critical"
        assert j["current_ratio"] == 0.0

    def test_critical_at_boundary(self):
        """Mix of fresh/stale near the p_c threshold → critical phase."""
        # For general domain, p_c = 0.08. With 100 entries, 8 fresh = exactly at p_c
        fresh = [{"id": f"f{i}", "content": "fresh", "type": "semantic",
                  "timestamp_age_days": 1, "source_trust": 0.9} for i in range(8)]
        stale = [{"id": f"s{i}", "content": "stale", "type": "semantic",
                  "timestamp_age_days": 500, "source_trust": 0.9} for i in range(92)]
        r = client.post("/v1/fleet/health-phase", headers=AUTH, json={"entries": fresh + stale, "domain": "general"})
        assert r.status_code == 200
        j = r.json()
        assert j["phase"] == "critical"
        assert abs(j["current_ratio"] - 0.08) < 0.01

    def test_domain_affects_threshold(self):
        """Fintech has higher p_c (0.28) so same ratio is sub_critical."""
        entries = [{"id": f"e{i}", "content": "x", "type": "semantic",
                    "timestamp_age_days": 1, "source_trust": 0.9} for i in range(2)]
        entries += [{"id": f"s{i}", "content": "x", "type": "semantic",
                     "timestamp_age_days": 500, "source_trust": 0.9} for i in range(8)]
        # 20% fresh ratio — above general p_c (0.08) but below fintech p_c (0.28)
        r = client.post("/v1/fleet/health-phase", headers=AUTH, json={"entries": entries, "domain": "fintech"})
        assert r.status_code == 200
        j = r.json()
        assert j["phase"] == "sub_critical"
        assert j["p_c_threshold"] == 0.28

    def test_empty_entries_rejected(self):
        r = client.post("/v1/fleet/health-phase", headers=AUTH, json={"entries": [], "domain": "general"})
        assert r.status_code == 400
