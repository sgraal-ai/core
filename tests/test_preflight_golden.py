"""Golden file test for /v1/preflight response schema drift detection.

Regenerate: python -m tests.golden.regenerate
"""
import json
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from api.main import app
from tests.golden.cases import GOLDEN_CASES, normalize_response

GOLDEN_PATH = os.path.join(os.path.dirname(__file__), "golden", "preflight_v1.json")

client = TestClient(app)


def _omega_bucket(omega):
    if omega < 30:
        return "low"
    elif omega < 60:
        return "medium"
    else:
        return "high"


class TestPreflightGolden:
    def test_golden_file_exists(self):
        """Golden file must exist — run python -m tests.golden.regenerate to create."""
        assert os.path.exists(GOLDEN_PATH), (
            f"Golden file not found at {GOLDEN_PATH}. "
            "Run: python -m tests.golden.regenerate"
        )

    def test_response_schema_stable(self):
        """All 10 golden cases produce responses with same key set and decision category."""
        with open(GOLDEN_PATH) as f:
            golden = json.load(f)

        diffs = []
        for i, case in enumerate(GOLDEN_CASES):
            r = client.post("/v1/preflight", json=case["input"],
                            headers={"Authorization": "Bearer sg_test_key_001"})
            assert r.status_code == 200, f"Case {case['name']}: HTTP {r.status_code}"
            normalized = normalize_response(r.json())
            expected = golden[i]

            # Check decision matches
            if normalized.get("recommended_action") != expected["decision"]:
                diffs.append(f"{case['name']}: decision {expected['decision']} → {normalized.get('recommended_action')}")

            # Check omega bucket matches (not exact value — scoring may have minor float drift)
            actual_bucket = _omega_bucket(normalized.get("omega_mem_final", 0))
            if actual_bucket != expected["omega_range"]:
                diffs.append(f"{case['name']}: omega_range {expected['omega_range']} → {actual_bucket}")

            # Check key set matches
            actual_keys = sorted(normalized.keys())
            if actual_keys != expected["response_keys"]:
                added = set(actual_keys) - set(expected["response_keys"])
                removed = set(expected["response_keys"]) - set(actual_keys)
                if added:
                    diffs.append(f"{case['name']}: new keys {added}")
                if removed:
                    diffs.append(f"{case['name']}: missing keys {removed}")

        assert not diffs, "Golden file drift detected:\n" + "\n".join(diffs)
