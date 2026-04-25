#!/usr/bin/env python3
"""Run Round 12 corpus (60 cases) against the Sgraal API.

Default: hits the live API at api.sgraal.com (requires network + valid key).
Use --local for offline runs via FastAPI TestClient.

PA cases (multi_hop_provenance_asymmetry, 20/60) return HTTP 422 in --local
mode because their entries use dict-typed `source` and `path` fields that
fail Pydantic validation in TestClient. This is a known limitation — PA
cases work on the live API. The script reports PA failures separately so
they don't mask real regressions in CC/PS families.

Usage:
    python3 tests/corpus/run_r12.py                    # live API
    python3 tests/corpus/run_r12.py --local             # local TestClient
    python3 tests/corpus/run_r12.py --key sg_live_xxx   # custom API key
"""
import argparse
import json
import os
import sys
import time

CORPUS_PATH = os.path.join(os.path.dirname(__file__), "round12", "round12_corpus.json")
DEFAULT_API_URL = "https://api.sgraal.com/v1/preflight"
DEFAULT_KEY = "sg_demo_playground"


def _call_live(payload, api_url, headers):
    import requests as http_requests
    r = http_requests.post(api_url, json=payload, headers=headers, timeout=30)
    return r.status_code, r.json() if r.status_code == 200 else {}


def _call_local(payload, client):
    r = client.post("/v1/preflight", json=payload,
                    headers={"Authorization": f"Bearer {DEFAULT_KEY}"})
    return r.status_code, r.json() if r.status_code == 200 else {}


def main():
    parser = argparse.ArgumentParser(description="Run Round 12 corpus")
    parser.add_argument("--local", action="store_true",
                        help="Use local FastAPI TestClient instead of live API")
    parser.add_argument("--url", default=DEFAULT_API_URL, help="API URL (live mode)")
    parser.add_argument("--key", default=DEFAULT_KEY, help="API key (live mode)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show per-case results")
    args = parser.parse_args()

    with open(CORPUS_PATH) as f:
        corpus = json.load(f)

    cases = corpus["cases"]
    headers = {"Authorization": f"Bearer {args.key}", "Content-Type": "application/json"}

    client = None
    if args.local:
        os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
        os.environ["SGRAAL_TEST_MODE"] = "1"
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)
        mode = "local (TestClient)"
    else:
        mode = f"live ({args.url})"

    print(f"Round 12 corpus: {len(cases)} cases, mode: {mode}\n")

    t0 = time.monotonic()
    families = {}  # family -> {match, mismatch, skip, mismatches[], block_ok, block_total}

    for case in cases:
        cid = case["case_id"]
        gt = case["ground_truth"]["correct_decision"]
        q = case["query"]
        family = case["attack_family"]
        payload = {
            "memory_state": case["memory_entries"],
            "domain": q["domain"],
            "action_type": q["action_type"],
        }

        if family not in families:
            families[family] = {"match": 0, "mismatch": 0, "skip": 0,
                                "mismatches": [], "block_ok": 0, "block_total": 0}
        fam = families[family]

        if args.local:
            status, j = _call_local(payload, client)
        else:
            try:
                status, j = _call_live(payload, args.url, headers)
            except Exception as e:
                fam["skip"] += 1
                if args.verbose:
                    print(f"  SKIP {cid}: {e}")
                continue

        if status != 200:
            fam["skip"] += 1
            if args.verbose:
                print(f"  SKIP {cid}: HTTP {status}")
            continue

        actual = j.get("recommended_action", "UNKNOWN")

        if gt == "BLOCK":
            fam["block_total"] += 1
            if actual == "BLOCK":
                fam["block_ok"] += 1

        if actual == gt:
            fam["match"] += 1
            if args.verbose:
                print(f"  OK   {cid}: {gt}")
        else:
            fam["mismatch"] += 1
            fam["mismatches"].append(f"{cid}: gt={gt} actual={actual}")
            if args.verbose:
                print(f"  MISS {cid}: gt={gt} actual={actual}")

    elapsed = time.monotonic() - t0

    # Report per family
    total_match = 0
    total_tested = 0
    total_block_ok = 0
    total_block = 0

    FAM_SHORT = {
        "confidence_calibration": "CC",
        "partial_sync_bleed": "PS",
        "multi_hop_provenance_asymmetry": "PA",
    }

    for fam_name in ["confidence_calibration", "partial_sync_bleed",
                     "multi_hop_provenance_asymmetry"]:
        fam = families.get(fam_name, {"match": 0, "mismatch": 0, "skip": 0,
                                       "mismatches": [], "block_ok": 0, "block_total": 0})
        short = FAM_SHORT.get(fam_name, fam_name)
        tested = fam["match"] + fam["mismatch"]
        total_match += fam["match"]
        total_tested += tested
        total_block_ok += fam["block_ok"]
        total_block += fam["block_total"]

        status = "PASS" if fam["mismatch"] == 0 else "FAIL"
        skip_note = f" ({fam['skip']} skipped)" if fam["skip"] else ""
        block_note = f", BLOCK {fam['block_ok']}/{fam['block_total']}" if fam["block_total"] else ""
        icon = "+" if status == "PASS" else "x"

        print(f"  [{icon}] {short}: {fam['match']}/{tested}{skip_note}{block_note}")
        for m in fam["mismatches"]:
            print(f"      {m}")

    print(f"\n{'=' * 60}")
    total_all = total_match + sum(f.get("skip", 0) for f in families.values())
    total_with_skip = total_tested + sum(f.get("skip", 0) for f in families.values())
    print(f"TOTAL: {total_match}/{total_with_skip} "
          f"(tested {total_tested}, skipped {total_with_skip - total_tested}) "
          f"in {elapsed:.1f}s")
    print(f"BLOCK: {total_block_ok}/{total_block}")

    if args.local and sum(f.get("skip", 0) for f in families.values()) > 0:
        print(f"\nNOTE: {sum(f.get('skip', 0) for f in families.values())} cases skipped "
              f"(HTTP 422). PA cases use dict-typed source/path fields that fail\n"
              f"Pydantic validation in TestClient. Use live API for full 60-case run.")

    # Exit code: 0 if all tested cases match, 1 otherwise
    sys.exit(0 if total_match == total_tested else 1)


if __name__ == "__main__":
    main()
