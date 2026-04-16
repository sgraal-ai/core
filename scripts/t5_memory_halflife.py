"""T5 — Memory Half-Life to F∞.

For each memory type, sweep timestamp_age_days from 0 to 200 and find
the age at which free_energy.F reaches 95% of F∞ (=2.27).

Writes: /Users/zsobrakpeter/core/research/results/memory_halflife.json
"""
import os
import sys
import json

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

OUTPUT = "/Users/zsobrakpeter/core/research/results/memory_halflife.json"
F_INFINITY = 2.27
THRESHOLD_FRACTION = 0.95
THRESHOLD_F = F_INFINITY * THRESHOLD_FRACTION

AGES = [0, 1, 2, 3, 5, 7, 10, 15, 20, 25, 30, 40, 50, 60, 75, 100, 125, 150, 175, 200]
TYPES = ["tool_state", "episodic", "semantic", "identity"]

SCORE_HISTORY = [50, 55, 60, 65, 70, 75, 80, 75, 70, 65]


def get_F(mem_type: str, age_days: float) -> float:
    """Run preflight for a single entry of the given type and age, return F."""
    payload = {
        "memory_state": [{
            "id": f"mem_{mem_type}_{age_days}",
            "content": f"Test entry of type {mem_type} aged {age_days} days",
            "type": mem_type,
            "timestamp_age_days": age_days,
            "source_trust": 0.8,
            "source_conflict": 0.0,
            "downstream_count": 1,
        }],
        "action_type": "reversible",
        "domain": "general",
        "score_history": SCORE_HISTORY,
    }
    r = client.post("/v1/preflight", json=payload, headers=AUTH)
    if r.status_code != 200:
        return None
    data = r.json()
    fe = data.get("free_energy", {})
    if not fe:
        return None
    return fe.get("F")


def main():
    per_type = {}
    all_curves = {}

    for mem_type in TYPES:
        print(f"\n--- Sweeping {mem_type} ---")
        curve = []
        lifetime = None
        F_by_age = {}
        for age in AGES:
            F = get_F(mem_type, age)
            curve.append((age, F))
            F_by_age[age] = F
            marker = ""
            if F is not None and F >= THRESHOLD_F and lifetime is None:
                lifetime = age
                marker = " <-- LIFETIME"
            print(f"  age={age:>4}d  F={F!r}{marker}")

        # Linear interpolation between the last-below and first-above points
        # for better precision on lifetime
        interp_lifetime = None
        for i in range(1, len(curve)):
            a_prev, f_prev = curve[i - 1]
            a_cur, f_cur = curve[i]
            if f_prev is None or f_cur is None:
                continue
            if f_prev < THRESHOLD_F <= f_cur:
                if f_cur == f_prev:
                    interp_lifetime = a_cur
                else:
                    frac = (THRESHOLD_F - f_prev) / (f_cur - f_prev)
                    interp_lifetime = round(a_prev + frac * (a_cur - a_prev), 1)
                break

        per_type[mem_type] = {
            "usable_lifetime_days": interp_lifetime if interp_lifetime is not None else lifetime,
            "F_at_day_0": F_by_age.get(0),
            "F_at_day_30": F_by_age.get(30),
            "F_at_day_100": F_by_age.get(100),
            "F_at_day_200": F_by_age.get(200),
            "reached_threshold": lifetime is not None,
        }
        all_curves[mem_type] = [{"age": a, "F": f} for a, f in curve]

    result = {
        "F_infinity": F_INFINITY,
        "threshold_fraction": THRESHOLD_FRACTION,
        "threshold_F": round(THRESHOLD_F, 4),
        "per_type": per_type,
        "sampled_ages": AGES,
        "full_curves": all_curves,
        "score_history_seed": SCORE_HISTORY,
    }

    with open(OUTPUT, "w") as f:
        json.dump(result, f, indent=2)

    print("\n=== T5 RESULTS ===")
    print(json.dumps({k: v for k, v in result.items() if k != "full_curves"}, indent=2))
    print(f"\nWrote {OUTPUT}")


if __name__ == "__main__":
    main()
