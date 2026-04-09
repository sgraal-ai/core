#!/usr/bin/env python3
"""Round 4 — Propagation corpus test (90 cases, 4 attack vectors + baseline)."""
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
CORPUS = "tests/corpus/round4_cases.json"


def call_api(rec):
    payload = {
        "memory_state": rec["memory_state"],
        "action_type": rec["action_type"],
        "domain": rec["domain"],
    }
    try:
        resp = http_requests.post(API_URL, json=payload, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            d = resp.json()
            return d.get("recommended_action"), d.get("omega_mem_final")
    except Exception:
        pass
    return "ERROR", None


def main():
    try:
        with open(CORPUS) as f:
            cases = json.load(f)
    except FileNotFoundError:
        print(f"Corpus not found: {CORPUS}")
        sys.exit(1)

    print(f"Round 4 — Propagation Corpus: {len(cases)} cases")
    print("=" * 55)

    t0 = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(call_api, c): c for c in cases}
        for fut in as_completed(futures):
            case = futures[fut]
            actual, omega = fut.result()
            expected = case["ground_truth"].get("expected_action", "")
            results.append({
                "test_id": case["test_id"],
                "scenario": case["scenario"],
                "expected": expected,
                "actual": actual,
                "omega": omega,
                "match": actual == expected,
            })

    elapsed = time.time() - t0

    # Breakdown by scenario
    by_scenario = defaultdict(lambda: {"total": 0, "passed": 0, "mismatches": []})
    for r in results:
        sc = by_scenario[r["scenario"]]
        sc["total"] += 1
        if r["match"]:
            sc["passed"] += 1
        else:
            sc["mismatches"].append(r)

    total_passed = sum(s["passed"] for s in by_scenario.values())
    total_cases = len(results)

    for sc_name in ["memory_injection_mid_chain", "cross_agent_drift_amplification",
                     "rag_retrieval_poisoning", "live_tool_api_drift", "clean_baseline"]:
        sc = by_scenario.get(sc_name, {"total": 0, "passed": 0, "mismatches": []})
        if sc["total"] == 0:
            continue
        icon = "\u2705" if sc["passed"] == sc["total"] else "\u274C"
        print(f"{icon} {sc_name}: {sc['passed']}/{sc['total']}")
        for m in sc["mismatches"][:3]:
            print(f"    {m['test_id']}: expected={m['expected']} actual={m['actual']} omega={m['omega']}")

    print(f"\n{total_passed}/{total_cases} passed in {elapsed:.1f}s")
    sys.exit(0 if total_passed == total_cases else 1)


if __name__ == "__main__":
    main()
