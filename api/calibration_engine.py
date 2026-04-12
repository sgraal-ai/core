"""Automated corpus calibration engine for Sgraal detection layers."""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from typing import Optional

try:
    import requests as http_requests
except ImportError:
    http_requests = None

# Decision boundary thresholds (default)
_DECISION_BOUNDARIES = {"WARN": 30, "ASK_USER": 55, "BLOCK": 75}


@dataclass
class CalibrationReport:
    total_cases: int = 0
    passed: int = 0
    mismatched: int = 0
    corpus_wrong: list = field(default_factory=list)
    threshold_wrong: list = field(default_factory=list)
    ambiguous: list = field(default_factory=list)
    suggested_adjustments: list = field(default_factory=list)
    human_review_required: list = field(default_factory=list)
    pass_rate: float = 0.0
    calibration_health: str = "HEALTHY"
    corpus_name: str = "all"
    details: list = field(default_factory=list)

    def to_dict(self):
        return {
            "total_cases": self.total_cases,
            "passed": self.passed,
            "mismatched": self.mismatched,
            "corpus_wrong": self.corpus_wrong,
            "threshold_wrong": self.threshold_wrong,
            "ambiguous": self.ambiguous,
            "suggested_adjustments": self.suggested_adjustments,
            "human_review_required": self.human_review_required,
            "pass_rate": self.pass_rate,
            "calibration_health": self.calibration_health,
            "corpus_name": self.corpus_name,
        }


class CalibrationEngine:
    def __init__(self, api_url: str = "https://api.sgraal.com", api_key: str = "sg_demo_playground"):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        if api_key != "sg_demo_playground":
            import logging
            logging.getLogger(__name__).warning(
                "Calibration with non-demo key '%s...' may pollute production state "
                "(vaccines, compromised agents, circuit breaker). Use sg_demo_playground for safe calibration.",
                api_key[:12])

    def _call_preflight(self, case: dict) -> Optional[dict]:
        if not http_requests:
            return None
        payload = {
            "memory_state": case["memory_state"],
            "domain": case.get("domain", "general"),
            "action_type": case.get("action_type", "informational"),
        }
        try:
            r = http_requests.post(f"{self.api_url}/v1/preflight", json=payload,
                                   headers=self.headers, timeout=15)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def classify_mismatch(self, case: dict, actual_response: dict) -> str:
        omega = actual_response.get("omega_mem_final", 0)
        expected = case.get("expected_decision", case.get("expected_consensus_collapse", ""))
        actual = actual_response.get("recommended_action", "")

        # All detection layers clean but expected BLOCK → corpus is wrong
        ts = actual_response.get("timestamp_integrity", "VALID")
        id_d = actual_response.get("identity_drift", "CLEAN")
        cc = actual_response.get("consensus_collapse", "CLEAN")
        pc = actual_response.get("provenance_chain_integrity", "CLEAN")
        all_clean = ts in ("VALID", "CLEAN") and id_d == "CLEAN" and cc == "CLEAN" and pc == "CLEAN"

        if all_clean and expected == "BLOCK":
            return "corpus_wrong"

        # Previously recalibrated
        if case.get("recalibrated"):
            return "corpus_wrong"

        # Far from boundary — corpus likely wrong
        _boundary = _DECISION_BOUNDARIES.get(expected, 50)
        if abs(omega - _boundary) > 20:
            return "corpus_wrong"

        # Close to boundary — threshold likely wrong
        if abs(omega - _boundary) <= 10:
            return "threshold_wrong"

        # Detection fired but not enough
        any_fired = ts not in ("VALID", "CLEAN") or id_d != "CLEAN" or cc != "CLEAN" or pc != "CLEAN"
        if any_fired:
            return "threshold_wrong"

        return "ambiguous"

    def suggest_threshold_adjustment(self, mismatches: list) -> list:
        suggestions = []

        # Count collapse_ratio near-misses
        collapse_near = [m for m in mismatches
                         if m.get("classification") == "threshold_wrong"
                         and m.get("actual_response", {}).get("collapse_ratio", 0) > 2.0
                         and m.get("actual_response", {}).get("collapse_ratio", 0) < 3.0]
        if len(collapse_near) >= 3:
            suggestions.append({
                "parameter": "collapse_ratio_threshold",
                "current": 3.0, "suggested": 2.8,
                "affected_cases": len(collapse_near),
                "reason": f"{len(collapse_near)} cases have collapse_ratio between 2.0-3.0",
            })

        # Count naturalness near-misses
        nat_near = [m for m in mismatches
                    if m.get("classification") == "threshold_wrong"
                    and m.get("actual_response", {}).get("naturalness_score", 1.0) > 0.3
                    and m.get("actual_response", {}).get("naturalness_score", 1.0) < 0.5]
        if len(nat_near) >= 3:
            suggestions.append({
                "parameter": "naturalness_synthetic_threshold",
                "current": 0.4, "suggested": 0.6,
                "affected_cases": len(nat_near),
                "reason": f"{len(nat_near)} cases have naturalness between 0.3-0.5",
            })

        return suggestions

    def run_corpus_cases(self, cases: list) -> CalibrationReport:
        report = CalibrationReport(total_cases=len(cases))
        mismatches_for_suggest = []

        for case in cases:
            resp = self._call_preflight(case)
            if resp is None:
                report.ambiguous.append(case.get("case_id", "?"))
                report.mismatched += 1
                continue

            # Determine expected fields
            expected_decision = (case.get("expected_decision")
                                 or case.get("expected", {}).get("recommended_action")
                                 or case.get("ground_truth", {}).get("expected_action")
                                 or case.get("ground_truth", {}).get("recommended_action", ""))
            actual_decision = resp.get("recommended_action", "")

            if expected_decision == actual_decision:
                report.passed += 1
            else:
                report.mismatched += 1
                classification = self.classify_mismatch(case, resp)
                case_id = case.get("case_id", case.get("test_id", "?"))
                detail = {
                    "case_id": case_id,
                    "expected": expected_decision,
                    "actual": actual_decision,
                    "omega": resp.get("omega_mem_final"),
                    "classification": classification,
                    "actual_response": {
                        "collapse_ratio": resp.get("collapse_ratio", 0),
                        "naturalness_score": resp.get("naturalness_score", 1.0),
                        "attack_surface_level": resp.get("attack_surface_level", "NONE"),
                    },
                }
                mismatches_for_suggest.append(detail)

                if classification == "corpus_wrong":
                    report.corpus_wrong.append(case_id)
                elif classification == "threshold_wrong":
                    report.threshold_wrong.append(case_id)
                else:
                    report.ambiguous.append(case_id)
                    report.human_review_required.append(case_id)

        report.pass_rate = round(report.passed / max(report.total_cases, 1), 4)

        if report.pass_rate >= 0.99:
            report.calibration_health = "HEALTHY"
        elif report.pass_rate >= 0.95:
            report.calibration_health = "DEGRADED"
        else:
            report.calibration_health = "CRITICAL"

        report.suggested_adjustments = self.suggest_threshold_adjustment(mismatches_for_suggest)
        report.details = mismatches_for_suggest

        return report


def _load_jsonl_corpus(path: str, layout: str) -> list:
    """Load a JSONL corpus file and normalize to calibration format."""
    cases = []
    try:
        for line in open(path):
            rec = json.loads(line)
            if layout == "input":
                cases.append({
                    "case_id": rec.get("test_id", "?"),
                    "memory_state": rec["input"]["memory_state"],
                    "action_type": rec["input"].get("action_type", "reversible"),
                    "domain": rec["input"].get("domain", "general"),
                    "expected_decision": rec["expected"]["recommended_action"],
                })
            else:
                cases.append({
                    "case_id": rec.get("test_id", "?"),
                    "memory_state": rec["memory_state"],
                    "action_type": rec.get("action_type", "reversible"),
                    "domain": rec.get("domain", "general"),
                    "expected_decision": (rec.get("ground_truth", {}).get("expected_action")
                                          or rec.get("ground_truth", {}).get("recommended_action", "")),
                })
    except Exception:
        pass
    return cases


def load_corpus_cases(corpus_name: str) -> list:
    """Load corpus cases by name."""
    import sys as _sys
    import importlib as _il
    import logging
    _log = logging.getLogger(__name__)

    # Resolve paths — works both locally and in Docker (/app)
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    corpus_dir = os.path.join(repo_root, "tests", "corpus")
    tests_dir = os.path.join(repo_root, "tests")

    # Fallback: if running from /app with PYTHONPATH=/app
    if not os.path.isdir(tests_dir):
        for candidate in ["/app/tests", os.path.join(os.getcwd(), "tests")]:
            if os.path.isdir(candidate):
                tests_dir = candidate
                corpus_dir = os.path.join(candidate, "corpus")
                break

    _log.info("calibration: repo_root=%s tests_dir=%s corpus_dir=%s exists=%s",
              repo_root, tests_dir, corpus_dir, os.path.isdir(corpus_dir))
    if corpus_dir not in _sys.path:
        _sys.path.insert(0, corpus_dir)
    cases = []

    # Rounds 1-4: JSONL files in tests/
    _JSONL_CORPORA = [
        ("round1", "sgraal_grok_joint_corpus.jsonl", "input"),
        ("round2", "sgraal_grok_sponsored_drift_corpus.jsonl", "top"),
        ("round2b", "sgraal_grok_subtle_drift_corpus.jsonl", "top"),
        ("round3", "sgraal_grok_hallucination_corpus.jsonl", "top"),
        ("round4", "sgraal_grok_propagation_corpus.jsonl", "top"),
    ]
    for round_name, filename, layout in _JSONL_CORPORA:
        if corpus_name in (round_name, "all"):
            fpath = os.path.join(tests_dir, filename)
            loaded = _load_jsonl_corpus(fpath, layout)
            _log.info("calibration: %s → %s (found=%s, cases=%d)", round_name, fpath, os.path.isfile(fpath), len(loaded))
            cases.extend(loaded)

    # Rounds 5-8: Python modules in tests/corpus/
    if corpus_name in ("round5", "all"):
        try:
            m = _il.import_module("round5_consensus_poisoning")
            cases.extend(m.CASES)
        except Exception:
            pass

    if corpus_name in ("round6", "all"):
        try:
            m = _il.import_module("round6_memory_time_attack")
            cases.extend(m.CASES)
        except Exception:
            pass

    if corpus_name in ("round7", "all"):
        try:
            m = _il.import_module("round7_identity_drift")
            cases.extend(m.CASES)
        except Exception:
            pass

    if corpus_name in ("round8", "all"):
        try:
            m = _il.import_module("round8_consensus_collapse")
            cases.extend(m.CASES)
        except Exception:
            pass

    return cases
