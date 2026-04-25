"""Tests for #783 Phase 1.5 — server-side self-authorship derivation."""
import os
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from api.self_authored import derive_is_self_authored


class TestDeriveIsSelfAuthored:
    def test_shallow_chain_is_self_authored(self):
        """Entry with depth ≤ 1 chain and no external indicators → True."""
        entry = {"id": "e1", "content": "test", "provenance_chain": ["agent_1"]}
        assert derive_is_self_authored(entry, "agent_1") is True

    def test_no_chain_is_self_authored(self):
        """Entry with no provenance_chain → True (self-authored default)."""
        entry = {"id": "e1", "content": "test"}
        assert derive_is_self_authored(entry, "agent_1") is True

    def test_empty_chain_is_self_authored(self):
        """Entry with empty provenance_chain → True."""
        entry = {"id": "e1", "content": "test", "provenance_chain": []}
        assert derive_is_self_authored(entry, "agent_1") is True

    def test_deep_chain_is_external(self):
        """Entry with depth > 1 chain → False (external provenance)."""
        entry = {"id": "e1", "content": "test", "provenance_chain": ["agent_1", "agent_2", "agent_3"]}
        assert derive_is_self_authored(entry, "agent_1") is False

    def test_external_source_type(self):
        """Entry with external source type → False."""
        entry = {"id": "e1", "content": "test", "source": "external_api", "provenance_chain": []}
        assert derive_is_self_authored(entry, "agent_1") is False

    def test_origin_mismatch_is_external(self):
        """Entry with declared != actual origin → False."""
        entry = {"id": "e1", "content": "test", "provenance_chain": [],
                 "source_declared_origin": "agent_1", "source_actual_origin": "agent_2"}
        assert derive_is_self_authored(entry, "agent_1") is False

    def test_sync_source_mismatch_is_external(self):
        """Entry with sync_source_id != request agent → False."""
        entry = {"id": "e1", "content": "test", "provenance_chain": [],
                 "sync_source_id": "agent_2"}
        assert derive_is_self_authored(entry, "agent_1") is False

    def test_sync_source_match_is_self_authored(self):
        """Entry with sync_source_id == request agent → True."""
        entry = {"id": "e1", "content": "test", "provenance_chain": [],
                 "sync_source_id": "agent_1"}
        assert derive_is_self_authored(entry, "agent_1") is True


class TestIntegration:
    def test_preflight_includes_derivation(self):
        """Preflight response should include self_authored_derivation."""
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)
        r = client.post("/v1/preflight", headers={"Authorization": "Bearer sg_test_key_001"}, json={
            "memory_state": [{"id": "e1", "content": "test", "type": "semantic",
                              "timestamp_age_days": 5, "source_trust": 0.9,
                              "source_conflict": 0.05, "downstream_count": 1}],
            "action_type": "reversible", "domain": "general", "dry_run": True,
        })
        assert r.status_code == 200
        j = r.json()
        assert "self_authored_derivation" in j
        sa = j["self_authored_derivation"]
        assert len(sa) == 1
        assert sa[0]["entry_id"] == "e1"
        assert sa[0]["derived_is_self_authored"] is True  # shallow chain

    def test_deep_chain_entry_flagged_external(self):
        """Entry with deep provenance chain should be flagged as external."""
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)
        r = client.post("/v1/preflight", headers={"Authorization": "Bearer sg_test_key_001"}, json={
            "memory_state": [{"id": "e1", "content": "test", "type": "semantic",
                              "timestamp_age_days": 5, "source_trust": 0.9,
                              "source_conflict": 0.05, "downstream_count": 1,
                              "provenance_chain": ["agent_a", "agent_b", "agent_c"]}],
            "action_type": "reversible", "domain": "general", "dry_run": True,
        })
        j = r.json()
        sa = j["self_authored_derivation"]
        assert sa[0]["derived_is_self_authored"] is False
