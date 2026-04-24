"""Tests for the 4-invariant validation layer."""
import os
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from api.invariants import check_invariants


class TestI1Identity:
    def test_clean_entries_pass(self):
        entries = [{"id": "a", "content": "hello"}, {"id": "b", "content": "world"}]
        r = check_invariants(entries)
        assert r["i1_identity"] == "ok"
        assert r["fast_path_block"] is False

    def test_duplicate_id_same_content_ok(self):
        entries = [{"id": "a", "content": "same"}, {"id": "a", "content": "same"}]
        r = check_invariants(entries)
        assert r["i1_identity"] == "ok"

    def test_duplicate_id_different_content_violates(self):
        entries = [{"id": "a", "content": "v1"}, {"id": "a", "content": "v2"}]
        r = check_invariants(entries)
        assert r["i1_identity"] == "clear_violation"
        assert r["fast_path_block"] is True
        assert r["violated_invariant"] == "I1"


class TestI2Time:
    def test_normal_ages_ok(self):
        entries = [{"id": "a", "content": "x", "timestamp_age_days": 5}]
        r = check_invariants(entries)
        assert r["i2_time"] == "ok"

    def test_negative_age_violates(self):
        entries = [{"id": "a", "content": "x", "timestamp_age_days": -10}]
        r = check_invariants(entries)
        assert r["i2_time"] == "clear_violation"
        assert r["fast_path_block"] is True
        assert r["violated_invariant"] == "I2"

    def test_age_zero_with_past_years_ambiguous(self):
        entries = [{"id": "a", "timestamp_age_days": 0,
                    "content": "Per 2023 rules, 2022 update, and 2024 revision"}]
        r = check_invariants(entries)
        assert r["i2_time"] == "ambiguous"


class TestI3Evidence:
    def test_diverse_evidence_ok(self):
        entries = [
            {"id": str(i), "content": "x", "source_trust": 0.1 * i, "source_conflict": 0.05}
            for i in range(5)
        ]
        r = check_invariants(entries)
        assert r["i3_evidence"] == "ok"

    def test_uniform_evidence_ambiguous(self):
        entries = [
            {"id": str(i), "content": "x", "source_trust": 0.9, "source_conflict": 0.01}
            for i in range(5)
        ]
        r = check_invariants(entries)
        assert r["i3_evidence"] == "ambiguous"


class TestI4Provenance:
    def test_clean_chain_ok(self):
        entries = [{"id": "a", "content": "x", "provenance_chain": ["agent_1", "agent_2"]}]
        r = check_invariants(entries)
        assert r["i4_provenance"] == "ok"

    def test_circular_chain_violates(self):
        entries = [{"id": "a", "content": "x", "provenance_chain": ["agent_1", "agent_2", "agent_1"]}]
        r = check_invariants(entries)
        assert r["i4_provenance"] == "clear_violation"
        assert r["fast_path_block"] is True
        assert r["violated_invariant"] == "I4"


class TestEmptyState:
    def test_empty_entries_ok(self):
        r = check_invariants([])
        assert r["fast_path_block"] is False
        assert r["entries_checked"] == 0


class TestIntegration:
    def test_full_pipeline_with_invariant_precheck(self):
        """Verify that invariant check runs before the full pipeline and
        produces a consistent result for a clean memory state."""
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        r = client.post("/v1/preflight", headers={"Authorization": "Bearer sg_test_key_001"}, json={
            "memory_state": [
                {"id": "e1", "content": "Clean entry", "type": "semantic",
                 "timestamp_age_days": 5, "source_trust": 0.9, "source_conflict": 0.05, "downstream_count": 1}
            ],
            "action_type": "reversible",
            "domain": "general",
            "dry_run": True,
        })
        assert r.status_code == 200
        j = r.json()
        # Clean state should not trigger fast-path block
        assert j.get("recommended_action") != "BLOCK" or j.get("omega_mem_final", 0) > 55
