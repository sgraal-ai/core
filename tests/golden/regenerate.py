"""Regenerate golden file for preflight response schema.

Usage: python -m tests.golden.regenerate
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from tests.golden.cases import GOLDEN_CASES, normalize_response

from fastapi.testclient import TestClient
from api.main import app

GOLDEN_PATH = os.path.join(os.path.dirname(__file__), "preflight_v1.json")


def main():
    client = TestClient(app)
    results = []
    for case in GOLDEN_CASES:
        r = client.post("/v1/preflight", json=case["input"],
                        headers={"Authorization": "Bearer sg_test_key_001"})
        assert r.status_code == 200, f"Case {case['name']}: HTTP {r.status_code}"
        normalized = normalize_response(r.json())
        results.append({"name": case["name"], "response_keys": sorted(normalized.keys()),
                        "decision": normalized.get("recommended_action"),
                        "omega_range": _omega_bucket(normalized.get("omega_mem_final", 0))})

    with open(GOLDEN_PATH, "w") as f:
        json.dump(results, f, indent=2, sort_keys=True)
    print(f"Golden file written: {GOLDEN_PATH} ({len(results)} cases)")


def _omega_bucket(omega):
    if omega < 30:
        return "low"
    elif omega < 60:
        return "medium"
    else:
        return "high"


if __name__ == "__main__":
    main()
