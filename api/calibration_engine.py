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


def load_corpus_cases(corpus_name: str) -> list:
    """Load corpus cases by name."""
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "corpus")
    cases = []

    if corpus_name in ("round6", "all"):
        try:
            import sys
            sys.path.insert(0, base)
            from round6_memory_time_attack import CASES as r6
            cases.extend(r6)
        except Exception:
            pass

    if corpus_name in ("round7", "all"):
        try:
            from round7_identity_drift import CASES as r7
            cases.extend(r7)
        except Exception:
            pass

    if corpus_name in ("round8", "all"):
        try:
            from round8_consensus_collapse import CASES as r8
            cases.extend(r8)
        except Exception:
            pass

    return cases
