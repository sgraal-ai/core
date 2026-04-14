#!/usr/bin/env python3
"""
Run Round 9 corpus through preflight and report detection rates.
"""
import json, sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def main():
    corpus_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "corpus", "round9_federated_poisoning.json")
    if not os.path.exists(corpus_path):
        # Generate first
        from scripts.generate_round9_corpus import main as gen
        gen()

    with open(corpus_path) as f:
        cases = json.load(f)

    print(f"Running {len(cases)} Round 9 cases through preflight...")
    print()

    results_by_vector = {}
    misses = []

    for i, case in enumerate(cases):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": case["memory_state"],
            "action_type": "irreversible",
            "domain": "fintech",
            "response_profile": "full",
        })

        if r.status_code != 200:
            misses.append({"case_id": case["id"], "error": r.status_code})
            continue

        j = r.json()
        action = j.get("recommended_action", "USE_MEMORY")
        omega = j.get("omega_mem_final", 0)

        expected = case["expected_decision"]
        expected_layer = case["expected_detection_layer"]
        actual_layer = j.get(expected_layer, "VALID") if expected_layer != "provenance_chain_integrity" else j.get("provenance_chain_integrity", "CLEAN")

        # Detection: did we catch it?
        # BLOCK expected → got BLOCK or WARN = caught (WARN is acceptable for detection)
        # WARN expected → got WARN, ASK_USER, or BLOCK = caught
        if expected == "BLOCK":
            detected = action in ("BLOCK", "WARN", "ASK_USER")
        else:
            detected = action in ("WARN", "ASK_USER", "BLOCK")

        # Layer detection
        layer_triggered = actual_layer in ("MANIPULATED", "SUSPICIOUS")

        vec = case["vector"]
        if vec not in results_by_vector:
            results_by_vector[vec] = {"total": 0, "detected": 0, "blocked": 0, "warned": 0,
                                       "layer_triggered": 0, "missed": [], "severity": {}}
        rv = results_by_vector[vec]
        rv["total"] += 1
        if detected:
            rv["detected"] += 1
        else:
            rv["missed"].append({"id": case["id"], "omega": omega, "action": action, "severity": case["attack_severity"]})
        if action == "BLOCK":
            rv["blocked"] += 1
        elif action in ("WARN", "ASK_USER"):
            rv["warned"] += 1
        if layer_triggered:
            rv["layer_triggered"] += 1

        sev = case["attack_severity"]
        if sev not in rv["severity"]:
            rv["severity"][sev] = {"total": 0, "detected": 0}
        rv["severity"][sev]["total"] += 1
        if detected:
            rv["severity"][sev]["detected"] += 1

        if (i + 1) % 30 == 0:
            print(f"  Processed {i + 1}/{len(cases)} cases...")

    # Report
    print()
    print("=" * 70)
    print("  ROUND 9: FEDERATED MEMORY POISONING — RESULTS")
    print("=" * 70)
    print()

    total_all = 0
    detected_all = 0
    for vec in ["provenance_erosion", "identity_hijack", "consensus_bleed", "tier3_rewrite"]:
        rv = results_by_vector.get(vec, {"total": 0, "detected": 0, "blocked": 0, "warned": 0, "layer_triggered": 0, "missed": [], "severity": {}})
        rate = rv["detected"] / max(rv["total"], 1)
        layer_rate = rv["layer_triggered"] / max(rv["total"], 1)
        total_all += rv["total"]
        detected_all += rv["detected"]

        print(f"  {vec}")
        print(f"    Detection rate:  {rv['detected']}/{rv['total']} ({rate*100:.1f}%)")
        print(f"    BLOCK:           {rv['blocked']}")
        print(f"    WARN/ASK:        {rv['warned']}")
        print(f"    Layer triggered: {rv['layer_triggered']}/{rv['total']} ({layer_rate*100:.1f}%)")
        for sev in ["subtle", "moderate", "aggressive"]:
            sd = rv["severity"].get(sev, {"total": 0, "detected": 0})
            sr = sd["detected"] / max(sd["total"], 1)
            print(f"    {sev:12s}:    {sd['detected']}/{sd['total']} ({sr*100:.0f}%)")
        if rv["missed"]:
            print(f"    Misses ({len(rv['missed'])}):")
            for m in rv["missed"][:5]:
                print(f"      {m['id']}: omega={m['omega']}, action={m['action']}, severity={m['severity']}")
        print()

    overall_rate = detected_all / max(total_all, 1)

    # F1 score: TP = detected, FP = 0 (all cases are attacks), FN = total - detected
    tp = detected_all
    fn = total_all - detected_all
    fp = 0  # All cases are true attacks
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 0.001)

    print("=" * 70)
    print(f"  OVERALL: {detected_all}/{total_all} ({overall_rate*100:.1f}%)")
    print(f"  F1 Score: {f1:.3f} (precision={precision:.3f}, recall={recall:.3f})")
    print(f"  Missed: {total_all - detected_all} cases")
    print("=" * 70)

    # Save results
    report = {
        "round": 9,
        "name": "Federated Memory Poisoning",
        "total_cases": total_all,
        "detected": detected_all,
        "detection_rate": round(overall_rate, 4),
        "f1_score": round(f1, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "vectors": {vec: {
            "total": rv["total"],
            "detected": rv["detected"],
            "rate": round(rv["detected"] / max(rv["total"], 1), 4),
            "blocked": rv["blocked"],
            "warned": rv["warned"],
            "layer_triggered": rv["layer_triggered"],
            "severity": rv["severity"],
            "missed_count": len(rv["missed"]),
        } for vec, rv in results_by_vector.items()},
    }
    with open("/tmp/round9_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Detailed results: /tmp/round9_results.json")


if __name__ == "__main__":
    main()
