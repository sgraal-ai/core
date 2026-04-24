#!/usr/bin/env python3
"""Analyze the impact of s_relevance on corpus decisions.

For each corpus case, runs preflight twice:
1. Normal — full pipeline
2. Counterfactual — s_relevance forced to 0

Reports which cases change decision and by how much omega shifts.

Usage:
    python3 scripts/analyze_s_relevance_impact.py [--output report.json]
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Setup
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from api.main import app, _load_benchmark_corpus

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def run_preflight(memory_state: list, action_type: str = "reversible",
                  domain: str = "general", custom_weights: dict = None) -> dict:
    """Run a single preflight call."""
    payload = {
        "memory_state": memory_state[:20],
        "action_type": action_type,
        "domain": domain,
        "dry_run": True,
    }
    if custom_weights:
        payload["custom_weights"] = custom_weights
    r = client.post("/v1/preflight", headers=AUTH, json=payload)
    if r.status_code != 200:
        return {"recommended_action": "ERROR", "omega_mem_final": -1}
    return r.json()


def analyze_corpus():
    """Run the full analysis on all corpus cases."""
    # Load benchmark corpus (rounds 1-11)
    cases = _load_benchmark_corpus()
    print(f"Loaded {len(cases)} benchmark corpus cases")

    # Also load R12 corpus if available
    r12_path = Path("tests/corpus/round12/round12_corpus.json")
    r12_cases = []
    if r12_path.exists():
        with open(r12_path) as f:
            r12_data = json.load(f)
        r12_raw = r12_data.get("cases", [])
        for c in r12_raw:
            entries = c.get("memory_entries", [])
            sanitized = []
            for e in entries:
                d = {}
                for k, v in e.items():
                    if k in ("attack_markers", "is_attack_entry"):
                        continue
                    if k == "source" and isinstance(v, dict):
                        d["source"] = v.get("declared_origin", "")
                        d["source_declared_origin"] = v.get("declared_origin", "")
                        d["source_actual_origin"] = v.get("actual_origin", "")
                    else:
                        d[k] = v
                sanitized.append(d)
            r12_cases.append({
                "case_id": c["case_id"],
                "memory_state": sanitized,
                "action_type": c["query"].get("action_type", "reversible"),
                "domain": c["query"].get("domain", "general"),
                "expected_action": c["ground_truth"]["correct_decision"],
                "round": 12,
            })
        print(f"Loaded {len(r12_cases)} R12 corpus cases")

    all_cases = cases + r12_cases
    total = len(all_cases)
    print(f"Total cases to analyze: {total}\n")

    # Standard weights from scoring engine
    from scoring_engine.omega_mem import WEIGHTS
    zero_relevance_weights = dict(WEIGHTS)
    zero_relevance_weights["s_relevance"] = 0.0

    results = []
    changed_count = 0
    t_start = time.monotonic()

    for i, case in enumerate(all_cases):
        ms = case.get("memory_state", [])
        at = case.get("action_type", "reversible")
        domain = case.get("domain", "general")
        case_id = case.get("case_id", f"case_{i}")
        rnd = case.get("round", 0)

        # Run normal
        r_normal = run_preflight(ms, at, domain)
        decision_normal = r_normal.get("recommended_action", "ERROR")
        omega_normal = r_normal.get("omega_mem_final", -1)

        # Run with s_relevance=0
        r_zero = run_preflight(ms, at, domain, custom_weights=zero_relevance_weights)
        decision_zero = r_zero.get("recommended_action", "ERROR")
        omega_zero = r_zero.get("omega_mem_final", -1)

        changed = decision_normal != decision_zero
        if changed:
            changed_count += 1

        entry = {
            "case_id": case_id,
            "round": rnd,
            "normal_decision": decision_normal,
            "zero_relevance_decision": decision_zero,
            "normal_omega": omega_normal,
            "zero_relevance_omega": omega_zero,
            "omega_delta": round(omega_zero - omega_normal, 2) if omega_normal >= 0 and omega_zero >= 0 else None,
            "decision_changed": changed,
        }
        results.append(entry)

        if (i + 1) % 50 == 0:
            elapsed = time.monotonic() - t_start
            print(f"  [{i+1}/{total}] {changed_count} changed so far ({elapsed:.1f}s)")

    elapsed = time.monotonic() - t_start

    # Build report
    changed_cases = [r for r in results if r["decision_changed"]]
    by_round: dict[int, dict] = {}
    for r in results:
        rnd = r["round"]
        by_round.setdefault(rnd, {"total": 0, "changed": 0, "cases": []})
        by_round[rnd]["total"] += 1
        if r["decision_changed"]:
            by_round[rnd]["changed"] += 1
            by_round[rnd]["cases"].append(r["case_id"])

    report = {
        "total_cases": total,
        "cases_changed": changed_count,
        "cases_unchanged": total - changed_count,
        "change_rate": round(changed_count / max(total, 1) * 100, 1),
        "elapsed_seconds": round(elapsed, 1),
        "changed_breakdown": [
            {"case_id": c["case_id"], "round": c["round"],
             "from": c["normal_decision"], "to": c["zero_relevance_decision"],
             "omega_delta": c["omega_delta"]}
            for c in changed_cases
        ],
        "by_round": {str(k): {"total": v["total"], "changed": v["changed"]} for k, v in sorted(by_round.items())},
    }

    # Summary
    print(f"\n{'='*60}")
    print(f"s_relevance Impact Analysis")
    print(f"{'='*60}")
    print(f"Total cases:     {total}")
    print(f"Cases changed:   {changed_count} ({report['change_rate']}%)")
    print(f"Cases unchanged: {total - changed_count}")
    print(f"Elapsed:         {elapsed:.1f}s")
    print()
    if changed_cases:
        print("Changed cases:")
        for c in changed_cases:
            print(f"  {c['case_id']} (R{c['round']}): {c['normal_decision']} → {c['zero_relevance_decision']} (Δω={c['omega_delta']})")
    else:
        print("No cases changed decision — s_relevance has zero impact on corpus decisions.")
    print()
    print("By round:")
    for rnd, data in sorted(by_round.items()):
        print(f"  R{rnd}: {data['changed']}/{data['total']} changed")

    return report


def main():
    report = analyze_corpus()

    # Output JSON if requested
    output_path = None
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]

    if output_path:
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to {output_path}")

    return report


if __name__ == "__main__":
    main()
