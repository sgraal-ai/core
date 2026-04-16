"""B3 — Healing Efficacy Analysis

Controlled simulation of healing impact on agent outcomes.

Since we don't have production-scale audit_log + outcome pairs yet, we run a
matched-pair synthetic experiment:
  - 100 NO-HEAL interactions (decision made on raw memory state)
  - 100 PRE-HEAL interactions (heal applied before decision)

Outcome assignment uses a logistic link around the empirical inflection
point theta = 46 (from research/results/calibration_curve.json):
  P(success | omega) = 1 - sigmoid((omega - 46) * 0.15)

This keeps the simulation faithful to our validated omega-outcome curve.
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
from pathlib import Path

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

RESULTS_PATH = Path("/Users/zsobrakpeter/core/research/results/healing_efficacy.json")
N_PER_ARM = 100
INFLECTION = 46.0
SLOPE = 0.15
RNG = random.Random(20260416)  # deterministic


def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def p_success(omega: float) -> float:
    return 1.0 - sigmoid((omega - INFLECTION) * SLOPE)


def make_memory_state(stress: float) -> list[dict]:
    """Build a small memory state whose riskiness scales with `stress` in [0, 1]."""
    # Higher stress -> older, less trusted, more conflict.
    base_age = 1.0 + stress * 120.0
    base_trust = max(0.1, 0.95 - stress * 0.7)
    base_conflict = min(0.9, stress * 0.8)
    entries = []
    for i in range(3):
        entries.append({
            "id": f"m{i}",
            "content": f"entry {i} about onboarding step {i}",
            "type": "semantic" if i % 2 == 0 else "episodic",
            "timestamp_age_days": base_age + i * 2.0,
            "source_trust": max(0.05, base_trust - i * 0.05),
            "source_conflict": min(0.95, base_conflict + i * 0.03),
            "downstream_count": 2 + i,
        })
    return entries


def preflight(memory_state: list[dict]) -> dict:
    resp = client.post(
        "/v1/preflight",
        headers=AUTH,
        json={
            "memory_state": memory_state,
            "action_type": "reversible",
            "domain": "general",
        },
    )
    resp.raise_for_status()
    return resp.json()


def heal(entry_id: str, action: str = "REFETCH") -> None:
    try:
        client.post(
            "/v1/heal",
            headers=AUTH,
            json={"entry_id": entry_id, "action": action},
        )
    except Exception:
        pass


def apply_heal_to_state(memory_state: list[dict], repair_plan: list[dict]) -> list[dict]:
    """Simulate REFETCH/VERIFY/REBUILD by rejuvenating the targeted entries."""
    if not repair_plan:
        return memory_state
    target_ids = {step.get("entry_id") for step in repair_plan if step.get("entry_id")}
    healed = []
    for e in memory_state:
        if e["id"] in target_ids:
            heal(e["id"], repair_plan[0].get("action", "REFETCH"))
            healed.append({
                **e,
                "timestamp_age_days": max(0.1, e["timestamp_age_days"] * 0.1),
                "source_trust": min(0.99, e["source_trust"] + 0.25),
                "source_conflict": max(0.01, e["source_conflict"] * 0.3),
            })
        else:
            healed.append(e)
    return healed


def sample_outcome(omega: float) -> str:
    return "success" if RNG.random() < p_success(omega) else "failure"


def mcnemar(b: int, c: int) -> float:
    """McNemar chi-square with continuity correction. b = NO_HEAL success & PRE_HEAL fail,
    c = NO_HEAL fail & PRE_HEAL success."""
    if (b + c) == 0:
        return 0.0
    return ((abs(b - c) - 1) ** 2) / (b + c)


def chi2_survival_1df(x: float) -> float:
    """P(X^2 > x) for 1 df. Using erfc on sqrt(x/2)."""
    if x <= 0:
        return 1.0
    return math.erfc(math.sqrt(x / 2.0))


def run() -> dict:
    no_heal: list[tuple[float, str]] = []
    post_heal: list[tuple[float, str, float]] = []  # (pre_omega, status, post_omega)

    # --- NO-HEAL arm ---
    for i in range(N_PER_ARM):
        stress = RNG.uniform(0.05, 0.95)
        state = make_memory_state(stress)
        pf = preflight(state)
        omega = float(pf.get("omega_mem_final", 50.0))
        status = sample_outcome(omega)
        no_heal.append((omega, status))

    # --- PRE-HEAL arm ---
    for i in range(N_PER_ARM):
        stress = RNG.uniform(0.05, 0.95)
        state = make_memory_state(stress)
        pf_before = preflight(state)
        pre_omega = float(pf_before.get("omega_mem_final", 50.0))
        repair = pf_before.get("repair_plan") or []
        healed_state = apply_heal_to_state(state, repair)
        pf_after = preflight(healed_state)
        post_omega = float(pf_after.get("omega_mem_final", pre_omega))
        status = sample_outcome(post_omega)
        post_heal.append((pre_omega, status, post_omega))

    success_rate_no_heal = sum(1 for _, s in no_heal if s == "success") / len(no_heal)
    success_rate_post_heal = sum(1 for _, s, _ in post_heal if s == "success") / len(post_heal)
    effect_size = success_rate_post_heal - success_rate_no_heal

    # Matched-pair McNemar table. Because the arms are independent (different
    # random stress draws), we pair them by rank of PRE omega to approximate
    # the matched design. A true paired design would use the same stress seed
    # across arms; we do the rank pairing to stay faithful to the design
    # intent while keeping the simulation honest.
    no_heal_sorted = sorted(no_heal, key=lambda r: r[0])
    post_heal_sorted = sorted(post_heal, key=lambda r: r[0])
    b = c = 0  # NO succ & PRE fail, NO fail & PRE succ
    for (_, s_no), (_, s_post, _) in zip(no_heal_sorted, post_heal_sorted):
        if s_no == "success" and s_post == "failure":
            b += 1
        elif s_no == "failure" and s_post == "success":
            c += 1
    chi2 = mcnemar(b, c)
    p_value = chi2_survival_1df(chi2)

    # Confidence tier based on sample size of the smaller arm.
    n_min = min(len(no_heal), len(post_heal))
    if n_min >= 100:
        confidence = "high"
    elif n_min >= 50:
        confidence = "medium"
    else:
        confidence = "low"

    healing_improves = (effect_size > 0.0) and (p_value < 0.05)

    result = {
        "n_no_heal": len(no_heal),
        "n_post_heal": len(post_heal),
        "success_rate_no_heal": round(success_rate_no_heal, 4),
        "success_rate_post_heal": round(success_rate_post_heal, 4),
        "effect_size": round(effect_size, 4),
        "mcnemar_chi2": round(chi2, 4),
        "p_value_approx": round(p_value, 6),
        "mcnemar_b_no_succ_post_fail": b,
        "mcnemar_c_no_fail_post_succ": c,
        "healing_improves_outcomes": bool(healing_improves),
        "confidence": confidence,
        "method": "simulated_controlled_experiment",
        "outcome_model": f"P(success)=1-sigmoid((omega-{INFLECTION})*{SLOPE})",
        "rng_seed": 20260416,
        "note": "Controlled simulation on synthetic data — replace with production audit_log when available",
    }
    return result


if __name__ == "__main__":
    result = run()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"\nSaved: {RESULTS_PATH}")
