#!/usr/bin/env python3
"""Run adversarial compound corpus against live API."""
import argparse
import json
import os
import sys

try:
    import requests as http_requests
except ImportError:
    print("pip install requests"); sys.exit(1)

# Generate corpus if needed
CORPUS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "adversarial_compound_corpus.jsonl")
if not os.path.exists(CORPUS_PATH):
    from generate_adversarial import save_corpus
    save_corpus(CORPUS_PATH)


def run(api_url, api_key):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    cases = [json.loads(line) for line in open(CORPUS_PATH)]

    passed = failed = errors_count = 0
    level_dist = {}
    severity_results = {"mild": [0, 0], "moderate": [0, 0], "severe": [0, 0]}
    fail_details = []

    for case in cases:
        payload = {"memory_state": case["memory_state"], "domain": case["domain"], "action_type": case["action_type"]}
        try:
            r = http_requests.post(f"{api_url}/v1/preflight", json=payload, headers=headers, timeout=15)
            if r.status_code != 200:
                fail_details.append(f"{case['case_id']}: HTTP {r.status_code}")
                failed += 1; errors_count += 1; continue
            d = r.json()
            actual_level = d.get("attack_surface_level", "NONE")
            level_dist[actual_level] = level_dist.get(actual_level, 0) + 1

            sev = case["severity"]
            # For adversarial cases, we check if the system detected ANYTHING (not NONE)
            detected = actual_level != "NONE"
            severity_results[sev][0] += 1  # total
            if detected:
                severity_results[sev][1] += 1  # detected
                passed += 1
            else:
                failed += 1
                if len(fail_details) < 10:
                    fail_details.append(f"{case['case_id']}: level=NONE severity={sev} omega={d.get('omega_mem_final')}")
        except Exception as e:
            fail_details.append(f"{case['case_id']}: {e}")
            failed += 1; errors_count += 1

    total = passed + failed
    detection_rate = round(passed / max(total, 1) * 100, 1)

    print(f"\n{'='*60}")
    print(f"Adversarial Compound Corpus")
    print(f"{'='*60}")
    print(f"Total: {total} cases | Detected: {passed} | Missed: {failed}")
    print(f"Detection rate: {detection_rate}%")
    print(f"\nAttack surface level distribution:")
    for level in ["NONE", "LOW", "MODERATE", "HIGH", "CRITICAL"]:
        count = level_dist.get(level, 0)
        bar = "#" * (count // 3)
        print(f"  {level:10s}: {count:3d} {bar}")
    print(f"\nDetection by severity:")
    for sev in ["mild", "moderate", "severe"]:
        t, d = severity_results[sev]
        rate = round(d / max(t, 1) * 100, 1)
        print(f"  {sev:10s}: {d}/{t} ({rate}%)")
    if fail_details:
        print(f"\nSample misses:")
        for f in fail_details[:5]:
            print(f"  {f}")
    print(f"{'='*60}")
    return detection_rate >= 50  # Success threshold: detect at least 50%


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://api.sgraal.com")
    parser.add_argument("--key", default="sg_demo_playground")
    args = parser.parse_args()
    sys.exit(0 if run(args.url, args.key) else 1)
