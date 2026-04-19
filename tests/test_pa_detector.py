"""Tests for Round 12 PA detector — provenance asymmetry signals in _check_provenance_chain."""
import os
import sys
import json

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.detection import _check_provenance_chain, _preprocess_entries
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

CORPUS_PATH = os.path.join(os.path.dirname(__file__), "corpus", "round12", "round12_corpus.json")


def _sanitize_entries(entries):
    """Convert R12 corpus entries to API-compatible format.

    The corpus has source as dict {declared_origin, actual_origin} and path objects.
    The API's MemoryEntryRequest expects source as Optional[str].
    Strip/convert fields the Pydantic model doesn't accept.
    """
    sanitized = []
    for e in entries:
        entry = {
            "id": e["id"],
            "content": e["content"],
            "type": e.get("type", "semantic"),
            "timestamp_age_days": e.get("timestamp_age_days", 0),
            "source_trust": e.get("source_trust", 0.8),
            "source_conflict": e.get("source_conflict", 0.05),
            "downstream_count": e.get("downstream_count", 1),
        }
        if e.get("provenance_chain"):
            entry["provenance_chain"] = e["provenance_chain"]
        if e.get("r_belief") is not None:
            entry["r_belief"] = e["r_belief"]
        # Convert source dict to string for API, but preserve original for detection
        src = e.get("source")
        if isinstance(src, dict):
            entry["source"] = src.get("declared_origin", "")
        elif isinstance(src, str):
            entry["source"] = src
        sanitized.append(entry)
    return sanitized


def _load_pa_cases():
    with open(CORPUS_PATH) as f:
        data = json.load(f)
    return [c for c in data["cases"] if c["attack_family"] == "multi_hop_provenance_asymmetry"]


# ---- Unit tests for individual signals ----

class TestMaxSingleHopJump:
    def test_no_chain_returns_zero(self):
        entries = [{"id": "e1", "content": "test", "type": "semantic",
                    "source_trust": 0.9, "provenance_chain": []}]
        result = _check_provenance_chain(entries)
        assert result["pa_signals"]["max_single_hop_jump"] == 0.0

    def test_stable_trust_below_threshold(self):
        entries = [
            {"id": "e1", "content": "hop 1", "type": "semantic", "source_trust": 0.85,
             "provenance_chain": ["a1"]},
            {"id": "e2", "content": "hop 2", "type": "semantic", "source_trust": 0.88,
             "provenance_chain": ["a1", "a2"]},
            {"id": "e3", "content": "hop 3", "type": "semantic", "source_trust": 0.86,
             "provenance_chain": ["a1", "a2", "a3"]},
        ]
        result = _check_provenance_chain(entries)
        assert result["pa_signals"]["max_single_hop_jump"] <= 0.07
        assert not result["pa_primary_gate"]

    def test_trust_jump_above_threshold(self):
        entries = [
            {"id": "e1", "content": "hop 1", "type": "semantic", "source_trust": 0.60,
             "provenance_chain": ["a1"]},
            {"id": "e2", "content": "hop 2", "type": "semantic", "source_trust": 0.90,
             "provenance_chain": ["a1", "a2"]},
        ]
        result = _check_provenance_chain(entries)
        assert result["pa_signals"]["max_single_hop_jump"] >= 0.28
        assert result["pa_primary_gate"]


class TestOriginMismatchRatio:
    def test_matching_origins(self):
        entries = [
            {"id": "e1", "content": "test", "type": "semantic", "source_trust": 0.9,
             "provenance_chain": ["a1"], "source": {"declared_origin": "a1", "actual_origin": "a1"}},
        ]
        result = _check_provenance_chain(entries)
        assert result["pa_signals"]["origin_mismatch_ratio"] == 0.0

    def test_mismatching_origins(self):
        entries = [
            {"id": "e1", "content": "test", "type": "semantic", "source_trust": 0.9,
             "provenance_chain": ["a1"], "source": {"declared_origin": "a1", "actual_origin": "a1"}},
            {"id": "e2", "content": "test2", "type": "semantic", "source_trust": 0.85,
             "provenance_chain": ["a1", "a2"], "source": {"declared_origin": "a2", "actual_origin": "a1"}},
        ]
        result = _check_provenance_chain(entries)
        assert result["pa_signals"]["origin_mismatch_ratio"] == 0.5
        assert "provenance_origin_mismatch:suspicious" in result["provenance_chain_flags"]


class TestEchoRatio:
    def test_no_echo(self):
        entries = [
            {"id": "e1", "content": "test", "type": "semantic", "source_trust": 0.9,
             "provenance_chain": ["a1"], "source": {"declared_origin": "a1", "actual_origin": "a1"}},
            {"id": "e2", "content": "test2", "type": "semantic", "source_trust": 0.85,
             "provenance_chain": ["a2"], "source": {"declared_origin": "a2", "actual_origin": "a2"}},
        ]
        result = _check_provenance_chain(entries)
        assert result["pa_signals"]["echo_ratio"] == 1.0

    def test_echo_detected(self):
        entries = [
            {"id": "e1", "content": "test", "type": "semantic", "source_trust": 0.9,
             "provenance_chain": ["a1"], "source": {"declared_origin": "src_a", "actual_origin": "real_src"}},
            {"id": "e2", "content": "test2", "type": "semantic", "source_trust": 0.85,
             "provenance_chain": ["a2"], "source": {"declared_origin": "src_b", "actual_origin": "real_src"}},
            {"id": "e3", "content": "test3", "type": "semantic", "source_trust": 0.87,
             "provenance_chain": ["a3"], "source": {"declared_origin": "src_c", "actual_origin": "real_src"}},
        ]
        result = _check_provenance_chain(entries)
        assert result["pa_signals"]["echo_ratio"] < 1.0
        assert "echo_amplification:suspicious" in result["provenance_chain_flags"]


class TestTrustEndpointDelta:
    def test_small_delta(self):
        entries = [
            {"id": "e1", "content": "hop 1", "type": "semantic", "source_trust": 0.85,
             "provenance_chain": ["a1"]},
            {"id": "e2", "content": "hop 2", "type": "semantic", "source_trust": 0.88,
             "provenance_chain": ["a1", "a2"]},
        ]
        result = _check_provenance_chain(entries)
        assert result["pa_signals"]["trust_endpoint_delta"] <= 0.1

    def test_large_delta(self):
        entries = [
            {"id": "e1", "content": "hop 1", "type": "semantic", "source_trust": 0.60,
             "provenance_chain": ["a1"]},
            {"id": "e2", "content": "hop 2", "type": "semantic", "source_trust": 0.95,
             "provenance_chain": ["a1", "a2", "a3"]},
        ]
        result = _check_provenance_chain(entries)
        assert result["pa_signals"]["trust_endpoint_delta"] > 0.1
        assert "trust_evolution_anomaly:suspicious" in result["provenance_chain_flags"]


# ---- Integration tests against Round 12 corpus ----

class TestPAAttackDetection:
    def test_all_pa_attack_cases_detected_by_detector(self):
        """All 11 PA attack cases must produce SUSPICIOUS or MANIPULATED from the detector directly."""
        pa_cases = _load_pa_cases()
        attacks = [c for c in pa_cases if not c["control"] and c["ground_truth"]["correct_decision"] == "BLOCK"]
        assert len(attacks) == 11, f"Expected 11 PA BLOCK attacks, got {len(attacks)}"

        missed = []
        for c in attacks:
            # Call detector directly with full corpus entries (including source dict)
            result = _check_provenance_chain(c["memory_entries"])
            integrity = result["provenance_chain_integrity"]
            if integrity == "CLEAN":
                missed.append(f"{c['case_id']}: detector returned CLEAN (signals={result.get('pa_signals')})")

        assert not missed, f"PA attacks not detected:\n" + "\n".join(missed)

    def test_pa_attacks_via_api_escalated(self):
        """PA attack cases should be escalated (not USE_MEMORY) through the API path."""
        pa_cases = _load_pa_cases()
        attacks = [c for c in pa_cases if not c["control"] and c["ground_truth"]["correct_decision"] == "BLOCK"]

        use_memory_count = 0
        for c in attacks:
            r = client.post("/v1/preflight", headers=AUTH, json={
                "memory_state": _sanitize_entries(c["memory_entries"]),
                "action_type": c["query"]["action_type"],
                "domain": c["query"]["domain"],
            })
            if r.status_code == 200 and r.json().get("recommended_action") == "USE_MEMORY":
                use_memory_count += 1

        # At minimum, the primary gate (trust jump) should prevent USE_MEMORY on most attacks
        assert use_memory_count <= 3, f"{use_memory_count}/11 PA attacks returned USE_MEMORY via API"


class TestPAControlCases:
    def test_no_pa_controls_manipulated_by_detector(self):
        """All 6 PA control cases must NOT return MANIPULATED from the detector."""
        pa_cases = _load_pa_cases()
        controls = [c for c in pa_cases if c["control"]]
        assert len(controls) == 6, f"Expected 6 PA controls, got {len(controls)}"

        manipulated = []
        for c in controls:
            result = _check_provenance_chain(c["memory_entries"])
            if result["provenance_chain_integrity"] == "MANIPULATED":
                manipulated.append(f"{c['case_id']}: MANIPULATED (signals={result.get('pa_signals')})")

        assert not manipulated, f"PA controls incorrectly MANIPULATED:\n" + "\n".join(manipulated)


# ---- Backward compatibility ----

class TestExistingDetectionUnchanged:
    def test_no_pa_signals_without_chains(self):
        """Entries without provenance chains should produce zero PA signals."""
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [{"id": "m1", "content": "simple test", "type": "semantic",
                              "timestamp_age_days": 1, "source_trust": 0.9,
                              "source_conflict": 0.1, "downstream_count": 1}],
            "action_type": "reversible", "domain": "general",
        })
        assert r.status_code == 200
        d = r.json()
        # Should not be BLOCK from PA detector
        assert d.get("recommended_action") in ("USE_MEMORY", "WARN")
