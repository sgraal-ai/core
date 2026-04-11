#!/usr/bin/env python3
"""Run Rounds 1-5 corpus tests against the live API (374 cases).
For Rounds 6-8, use: round6_memory_time_attack.py, round7_identity_drift.py, round8_consensus_collapse.py
For adversarial compound corpus: run_adversarial.py"""
import json
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests as http_requests
except ImportError:
    print("requests package required: pip install requests")
    sys.exit(1)

API_URL = "https://api.sgraal.com/v1/preflight"
HEADERS = {"Authorization": "Bearer sg_demo_playground", "Content-Type": "application/json"}

CORPORA = [
    ("tests/sgraal_grok_joint_corpus.jsonl", "Round 1 — Joint Benchmark", "input"),
    ("tests/sgraal_grok_sponsored_drift_corpus.jsonl", "Round 2 — Sponsored Drift", "top"),
    ("tests/sgraal_grok_subtle_drift_corpus.jsonl", "Round 2b — Subtle Drift", "top"),
    ("tests/sgraal_grok_hallucination_corpus.jsonl", "Round 3 — Hallucination", "top"),
    ("tests/sgraal_grok_propagation_corpus.jsonl", "Round 4 — Propagation", "top"),
]


def call_api(rec, layout):
    if layout == "input":
        payload = {"memory_state": rec["input"]["memory_state"], "action_type": rec["input"]["action_type"], "domain": rec["input"]["domain"]}
        for k in ("score_history", "compliance_profile", "steps"):
            if rec["input"].get(k):
                payload[k] = rec["input"][k]
        expected = rec["expected"]["recommended_action"]
    else:
        payload = {"memory_state": rec["memory_state"], "action_type": rec["action_type"], "domain": rec["domain"]}
        expected = rec["ground_truth"].get("expected_action") or rec["ground_truth"].get("recommended_action", "")
    try:
        resp = http_requests.post(API_URL, json=payload, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            d = resp.json()
            return expected, d.get("recommended_action"), d.get("omega_mem_final")
    except Exception:
        pass
    return expected, "ERROR", None


def run_corpus(path, name, layout):
    try:
        records = [json.loads(line) for line in open(path)]
    except FileNotFoundError:
        return name, 0, 0, [f"File not found: {path}"]

    results = []
    for rec in records:
        expected, actual, omega = call_api(rec, layout)
        tid = rec.get("test_id", "?")
        results.append((tid, expected, actual, omega))

    passed = sum(1 for _, e, a, _ in results if e == a)
    total = len(results)
    mismatches = [(tid, e, a, o) for tid, e, a, o in results if e != a]
    return name, passed, total, mismatches


def main():
    print("=" * 60)
    print("Sgraal Corpus Test Suite")
    print("=" * 60)

    grand_passed = 0
    grand_total = 0
    all_passed = True
    t0 = time.time()

    for path, name, layout in CORPORA:
        name, passed, total, mismatches = run_corpus(path, name, layout)
        grand_passed += passed
        grand_total += total
        status = "PASS" if passed == total else "FAIL"
        icon = "\u2705" if passed == total else "\u274C"
        print(f"\n{icon} {name}: {passed}/{total} ({status})")
        if mismatches:
            all_passed = False
            for tid, exp, act, omega in sorted(mismatches)[:5]:
                print(f"    {tid}: expected={exp} actual={act} omega={omega}")
            if len(mismatches) > 5:
                print(f"    ... and {len(mismatches) - 5} more")

    # Round 5 — Python module corpus
    try:
        import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from round5_consensus_poisoning import CASES as r5_cases
        r5_passed = r5_failed = 0
        r5_mismatches = []
        for case in r5_cases:
            payload = {"memory_state": case["memory_state"], "domain": case["domain"], "action_type": case["action_type"]}
            try:
                resp = http_requests.post(API_URL, json=payload, headers=HEADERS, timeout=15)
                if resp.status_code == 200:
                    d = resp.json()
                    if d.get("recommended_action") == case["expected_decision"]:
                        r5_passed += 1
                    else:
                        r5_failed += 1
                        r5_mismatches.append((case["case_id"], case["expected_decision"], d.get("recommended_action"), d.get("omega_mem_final")))
                else:
                    r5_failed += 1
            except Exception:
                r5_failed += 1
        r5_total = r5_passed + r5_failed
        grand_passed += r5_passed
        grand_total += r5_total
        status = "PASS" if r5_passed == r5_total else "FAIL"
        icon = "\u2705" if r5_passed == r5_total else "\u274C"
        print(f"\n{icon} Round 5 — Consensus Poisoning: {r5_passed}/{r5_total} ({status})")
        if r5_mismatches:
            all_passed = False
            for tid, exp, act, omega in sorted(r5_mismatches)[:5]:
                print(f"    {tid}: expected={exp} actual={act} omega={omega}")
    except ImportError:
        print("\n⚠️  Round 5 — skipped (round5_consensus_poisoning.py not found)")

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"TOTAL: {grand_passed}/{grand_total} in {elapsed:.1f}s")
    print(f"{'=' * 60}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
