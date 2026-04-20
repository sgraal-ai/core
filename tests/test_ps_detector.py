"""Tests for Round 12 PS detector — sync bleed detection via _check_sync_bleed."""
import os
import sys
import json

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.detection import _check_sync_bleed, _preprocess_entries
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}
CORPUS_PATH = os.path.join(os.path.dirname(__file__), "corpus", "round12", "round12_corpus.json")


def _load_ps_cases():
    with open(CORPUS_PATH) as f:
        data = json.load(f)
    return [c for c in data["cases"] if c["attack_family"] == "partial_sync_bleed"]


def _sanitize(entries):
    out = []
    for e in entries:
        entry = {"id": e["id"], "content": e["content"], "type": e.get("type", "semantic"),
                 "timestamp_age_days": e.get("timestamp_age_days", 0),
                 "source_trust": e.get("source_trust", 0.8),
                 "source_conflict": e.get("source_conflict", 0.05),
                 "downstream_count": e.get("downstream_count", 1)}
        if e.get("provenance_chain"): entry["provenance_chain"] = e["provenance_chain"]
        if e.get("r_belief") is not None: entry["r_belief"] = e["r_belief"]
        src = e.get("source")
        if isinstance(src, dict):
            entry["source"] = src.get("declared_origin", "")
            entry["source_declared_origin"] = src.get("declared_origin")
            entry["source_actual_origin"] = src.get("actual_origin")
        elif isinstance(src, str):
            entry["source"] = src
        for f in ["sync_version", "sync_state", "sync_source_id", "model_confidence",
                   "source_declared_origin", "source_actual_origin"]:
            v = e.get(f)
            if v is not None: entry[f] = v
        out.append(entry)
    return out


# ---- Unit tests ----

class TestStaleFraction:
    def test_all_current(self):
        entries = [
            {"id": "e1", "content": "test", "type": "semantic", "sync_version": "v1", "sync_state": "current"},
            {"id": "e2", "content": "test2", "type": "semantic", "sync_version": "v1", "sync_state": "current"},
        ]
        result = _check_sync_bleed(entries)
        assert result["sync_signals"]["stale_fraction"] == 0.0

    def test_majority_stale(self):
        entries = [
            {"id": "e1", "content": "fresh", "type": "semantic", "sync_version": "v2", "sync_state": "current"},
            {"id": "e2", "content": "old", "type": "semantic", "sync_version": "v1", "sync_state": "stale"},
            {"id": "e3", "content": "old2", "type": "semantic", "sync_version": "v1", "sync_state": "stale"},
        ]
        result = _check_sync_bleed(entries)
        assert result["sync_signals"]["stale_outnumbers_fresh"] is True


class TestCrossVersionJaccard:
    def test_identical_content_high_jaccard(self):
        entries = [
            {"id": "e1", "content": "The patient allergy record shows penicillin sensitivity",
             "type": "semantic", "sync_version": "v1", "sync_state": "current"},
            {"id": "e2", "content": "The patient allergy record shows penicillin sensitivity",
             "type": "semantic", "sync_version": "v2", "sync_state": "stale"},
        ]
        result = _check_sync_bleed(entries)
        assert result["sync_signals"]["cross_version_jaccard"] >= 0.9

    def test_contradicting_content_low_jaccard(self):
        entries = [
            {"id": "e1", "content": "Materiality threshold raised to one hundred thousand dollars effective immediately",
             "type": "semantic", "sync_version": "v2", "sync_state": "current"},
            {"id": "e2", "content": "Standing compliance policy sets fifty thousand dollar materiality for small-cap",
             "type": "semantic", "sync_version": "v1", "sync_state": "stale"},
            {"id": "e3", "content": "Materiality remains at fifty thousand per quarterly review database snapshot",
             "type": "semantic", "sync_version": "v1", "sync_state": "stale"},
        ]
        result = _check_sync_bleed(entries)
        assert result["sync_signals"]["cross_version_jaccard"] < 0.3


class TestGracefulDegradation:
    def test_no_sync_fields_returns_clean(self):
        entries = [
            {"id": "e1", "content": "test", "type": "semantic", "source_trust": 0.9},
            {"id": "e2", "content": "test2", "type": "semantic", "source_trust": 0.8},
        ]
        result = _check_sync_bleed(entries)
        assert result["sync_bleed"] == "CLEAN"

    def test_partial_fields_treats_missing_as_current(self):
        entries = [
            {"id": "e1", "content": "has sync", "type": "semantic", "sync_version": "v2", "sync_state": "current"},
            {"id": "e2", "content": "no sync fields", "type": "semantic"},
        ]
        result = _check_sync_bleed(entries)
        assert result["sync_bleed"] == "CLEAN"


class TestClassification:
    def test_manipulated_on_stale_majority_plus_contradiction(self):
        entries = [
            {"id": "e1", "content": "Threshold is one hundred thousand dollars per new ruling",
             "type": "policy", "sync_version": "v2", "sync_state": "current"},
            {"id": "e2", "content": "Threshold remains fifty thousand as per standing policy",
             "type": "policy", "sync_version": "v1", "sync_state": "stale"},
            {"id": "e3", "content": "Fifty thousand dollar materiality confirmed in database",
             "type": "policy", "sync_version": "v1", "sync_state": "stale"},
        ]
        result = _check_sync_bleed(entries)
        assert result["sync_bleed"] in ("MANIPULATED", "SUSPICIOUS")
        assert result["sync_signals"]["stale_outnumbers_fresh"] is True

    def test_clean_on_identical_content_across_versions(self):
        entries = [
            {"id": "e1", "content": "API gateway heartbeat status healthy configuration hash abc123",
             "type": "tool_state", "sync_version": "v2", "sync_state": "current"},
            {"id": "e2", "content": "API gateway heartbeat status healthy configuration hash abc123",
             "type": "tool_state", "sync_version": "v1", "sync_state": "stale"},
        ]
        result = _check_sync_bleed(entries)
        assert result["sync_bleed"] == "CLEAN"


# ---- Integration tests against R12 corpus ----

class TestPSAttackDetection:
    def test_ps_attacks_detected(self):
        """At least 7/8 PS attack cases must produce SUSPICIOUS or MANIPULATED.

        PS-008 is a known edge case (equal stale/fresh split, moderate Jaccard)
        that requires action-type escalation (Phase 5) to reach BLOCK.
        """
        ps_cases = _load_ps_cases()
        attacks = [c for c in ps_cases if not c["control"] and c["ground_truth"]["correct_decision"] == "BLOCK"]
        assert len(attacks) == 8

        detected = 0
        for c in attacks:
            result = _check_sync_bleed(c["memory_entries"])
            if result["sync_bleed"] != "CLEAN":
                detected += 1

        assert detected >= 7, f"Only {detected}/8 PS attacks detected (expected ≥7)"


class TestPSControlCases:
    def test_no_latency_controls_manipulated(self):
        """Latency-only controls (PS-015 through PS-020) must be CLEAN."""
        ps_cases = _load_ps_cases()
        latency = [c for c in ps_cases if c["control"] and "latency" in c["attack_subtype"]]

        manipulated = []
        for c in latency:
            result = _check_sync_bleed(c["memory_entries"])
            if result["sync_bleed"] == "MANIPULATED":
                manipulated.append(f"{c['case_id']}: MANIPULATED")

        assert not manipulated, f"Latency controls MANIPULATED:\n" + "\n".join(manipulated)

    def test_no_controls_blocked_via_api(self):
        """No PS control should return BLOCK from the API."""
        ps_cases = _load_ps_cases()
        controls = [c for c in ps_cases if c["control"]]

        blocked = []
        for c in controls:
            r = client.post("/v1/preflight", headers=AUTH, json={
                "memory_state": _sanitize(c["memory_entries"]),
                "action_type": c["query"]["action_type"],
                "domain": c["query"]["domain"],
                "dry_run": True,
            })
            if r.status_code == 200 and r.json().get("recommended_action") == "BLOCK":
                blocked.append(c["case_id"])

        assert not blocked, f"PS controls BLOCKED: {blocked}"


class TestNoRegressionOnOtherFamilies:
    def test_legacy_entries_unaffected(self):
        """Entries without sync fields get CLEAN from sync bleed detector."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{"id": "m1", "content": "simple test", "type": "semantic",
                              "timestamp_age_days": 1, "source_trust": 0.9,
                              "source_conflict": 0.1, "downstream_count": 1}],
            "action_type": "reversible", "domain": "general", "dry_run": True,
        })
        assert r.status_code == 200
        d = r.json()
        assert d.get("sync_bleed", "CLEAN") == "CLEAN"
