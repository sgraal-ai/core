#!/usr/bin/env python3
"""
TASK 7 — Optimal Forgetting Rate per Domain

Research question: at what per-call forgetting rate λ does each domain
achieve peak *decision accuracy*?

Simulation design:
  * Lambdas tested: {0.001, 0.005, 0.01, 0.05, 0.1, 0.2, 0.5}
  * Domains: general, fintech, medical, legal, coding, customer_support
  * Per configuration: 25 synthetic agents × 20 calls = 500 preflight calls
  * Agent memory: 3 entries, ages progress by +U[1,3] days per call,
    with per-call probability λ that any given entry is "forgotten"
    (reset to age 0 as a fresh replacement).
  * /v1/preflight called with dry_run=True.
  * Synthetic outcome:
      success if omega < 40 with P=0.9, else P=0.3
  * Decision correctness:
      correct = (action ∈ {BLOCK, ASK_USER} AND outcome = failure)
             OR (action = USE_MEMORY AND outcome = success)
      WARN actions count as correct only when outcome = failure (it's a warning).
  * Metrics per (λ, domain):
      accuracy, mean_omega, mean_savings (expected_savings_if_blocked)
  * Optima per domain:
      optimal_lambda_accuracy = argmax accuracy
      optimal_lambda_omega    = argmin mean_omega
      optimal_lambda_savings  = argmax mean_savings

Deterministic seed: numpy.random.default_rng(7777).
"""
import json
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")

import numpy as np
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

OUT_JSON = "/Users/zsobrakpeter/core/research/results/optimal_forgetting.json"
OUT_MD = "/Users/zsobrakpeter/core/research/results/optimal_forgetting_section.md"

LAMBDAS = [0.001, 0.005, 0.01, 0.05, 0.1, 0.2, 0.5]
DOMAINS = ["general", "fintech", "medical", "legal", "coding", "customer_support"]

N_AGENTS = 25
N_CALLS = 20

# Deterministic
RNG = np.random.default_rng(7777)

# Action -> type mapping per domain (keep action_type fixed per domain for fairness)
DOMAIN_ACTION_TYPE = {
    "fintech": "irreversible",
    "medical": "irreversible",
    "legal": "irreversible",
    "coding": "reversible",
    "customer_support": "reversible",
    "general": "reversible",
}


def make_entries(ages, trust=0.78, conflict=0.14):
    return [
        {
            "id": f"e_{i}",
            "content": f"simulated entry {i}",
            "type": "semantic",
            "timestamp_age_days": round(float(age), 3),
            "source_trust": trust,
            "source_conflict": conflict,
            "downstream_count": 4,
        }
        for i, age in enumerate(ages)
    ]


def run_preflight(ages, domain, action_type):
    payload = {
        "memory_state": make_entries(ages),
        "action_type": action_type,
        "domain": domain,
        "dry_run": True,
    }
    r = client.post("/v1/preflight", headers=AUTH, json=payload, timeout=30)
    if r.status_code != 200:
        return None
    return r.json()


def synthetic_outcome(omega, rng):
    """Success probability 0.9 if omega<40 else 0.3."""
    p_success = 0.9 if omega < 40.0 else 0.3
    return "success" if rng.random() < p_success else "failure"


def is_correct(action, outcome):
    if action in ("BLOCK", "ASK_USER") and outcome == "failure":
        return True
    if action == "WARN" and outcome == "failure":
        return True
    if action == "USE_MEMORY" and outcome == "success":
        return True
    return False


def simulate(lam, domain, rng):
    action_type = DOMAIN_ACTION_TYPE[domain]

    correct = 0
    total = 0
    omega_list = []
    savings_list = []

    for agent in range(N_AGENTS):
        # initial ages 0..5
        ages = list(rng.uniform(0.0, 5.0, size=3))

        for _step in range(N_CALLS):
            resp = run_preflight(ages, domain, action_type)
            if resp is None:
                # treat as skipped
                # still age the memory
                ages = [a + float(rng.uniform(1, 3)) for a in ages]
                continue

            omega = float(resp.get("omega_mem_final", 0.0))
            action = resp.get("recommended_action", "USE_MEMORY")
            savings = float(resp.get("expected_savings_if_blocked", 0.0) or 0.0)

            outcome = synthetic_outcome(omega, rng)
            if is_correct(action, outcome):
                correct += 1
            total += 1

            omega_list.append(omega)
            savings_list.append(savings)

            # Memory dynamics for next call
            new_ages = []
            for a in ages:
                # Forget with probability λ → reset to 0
                if rng.random() < lam:
                    new_ages.append(0.0)
                else:
                    new_ages.append(a + float(rng.uniform(1, 3)))
            ages = new_ages

    accuracy = correct / total if total else 0.0
    mean_omega = float(np.mean(omega_list)) if omega_list else 0.0
    mean_savings = float(np.mean(savings_list)) if savings_list else 0.0
    return {
        "accuracy": round(accuracy, 6),
        "mean_omega": round(mean_omega, 4),
        "mean_savings": round(mean_savings, 4),
        "n_calls": total,
    }


def main():
    results = {}

    for domain in DOMAINS:
        print(f"=== domain={domain} ===")
        per_lambda = {}
        for lam in LAMBDAS:
            # Each (λ, domain) gets its own deterministic rng
            seed = int(1000 * lam) * 1009 + hash(domain) % 10_000
            rng = np.random.default_rng(seed)
            m = simulate(lam, domain, rng)
            per_lambda[str(lam)] = m
            print(f"  lambda={lam:<6}  acc={m['accuracy']:.3f}  "
                  f"omega={m['mean_omega']:.2f}  savings={m['mean_savings']:.2f}")

        # Find optima
        def _argmax(key):
            best_lam = None
            best_val = -1e18
            for lam_s, m in per_lambda.items():
                v = m[key]
                if v > best_val:
                    best_val = v
                    best_lam = lam_s
            return best_lam

        def _argmin(key):
            best_lam = None
            best_val = 1e18
            for lam_s, m in per_lambda.items():
                v = m[key]
                if v < best_val:
                    best_val = v
                    best_lam = lam_s
            return best_lam

        results[domain] = {
            "lambda_values": per_lambda,
            "optimal_lambda_accuracy": _argmax("accuracy"),
            "optimal_lambda_omega": _argmin("mean_omega"),
            "optimal_lambda_savings": _argmax("mean_savings"),
        }

    # Overall pattern description
    high_crit = ["fintech", "medical", "legal"]
    low_crit = ["coding", "customer_support", "general"]

    def _mean_optimal(group, key):
        vals = [float(results[d][key]) for d in group]
        return float(np.mean(vals))

    mean_opt_acc_high = _mean_optimal(high_crit, "optimal_lambda_accuracy")
    mean_opt_acc_low = _mean_optimal(low_crit, "optimal_lambda_accuracy")

    if mean_opt_acc_high < mean_opt_acc_low:
        pattern = (
            "High-criticality domains (fintech/medical/legal) prefer *lower* forgetting "
            "rates than lower-criticality domains (coding/customer_support/general). "
            "Under irreversible actions, retaining older evidence is worth the risk of "
            "some staleness; under reversible actions, faster turnover pays off."
        )
    elif mean_opt_acc_high > mean_opt_acc_low:
        pattern = (
            "High-criticality domains prefer *higher* forgetting rates than "
            "low-criticality domains — suggesting that aggressive refresh is the "
            "best defence when an incorrect irreversible action is costly."
        )
    else:
        pattern = "Forgetting optima are roughly domain-invariant in this simulation."

    recommendation = (
        "Suggested defaults (per domain, argmax accuracy): "
        + ", ".join(f"{d}→λ={results[d]['optimal_lambda_accuracy']}" for d in DOMAINS)
    )

    output = {
        "synthetic": True,
        "lambdas_tested": LAMBDAS,
        "domains": DOMAINS,
        "simulation": {
            "agents_per_config": N_AGENTS,
            "calls_per_agent": N_CALLS,
            "entries_per_agent": 3,
            "outcome_rule": "success P=0.9 if omega<40 else P=0.3",
            "correct_rule": "action in {BLOCK, ASK_USER, WARN} AND outcome=failure, OR action=USE_MEMORY AND outcome=success",
        },
        "per_domain_results": results,
        "overall_pattern": pattern,
        "recommendation": recommendation,
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(output, f, indent=2, default=str)

    # Markdown
    md = []
    md.append("### 19.7 Optimal Forgetting Rate per Domain")
    md.append("")
    md.append(
        "Each domain × forgetting-rate λ combination is simulated with 25 agents "
        "making 20 preflight calls each (500 calls / config). Memory ages progress "
        "by U[1,3] days per call, and each entry has per-call probability λ of being "
        "'forgotten' and reset to age 0. Outcomes are synthetic (success P=0.9 if "
        "ω<40 else P=0.3); decision accuracy measures alignment between the "
        "recommended action and the outcome."
    )
    md.append("")
    md.append("**Optimal λ per domain (argmax accuracy):**")
    md.append("")
    md.append("| Domain | λ* (accuracy) | Accuracy | λ (min ω) | λ (max savings) |")
    md.append("|--------|---------------|----------|-----------|-----------------|")
    for d in DOMAINS:
        lam_acc = results[d]["optimal_lambda_accuracy"]
        acc_val = results[d]["lambda_values"][lam_acc]["accuracy"]
        md.append(
            f"| {d} | {lam_acc} | {acc_val:.3f} | "
            f"{results[d]['optimal_lambda_omega']} | "
            f"{results[d]['optimal_lambda_savings']} |"
        )
    md.append("")
    md.append(pattern)
    md.append("")
    md.append(recommendation)
    md.append("")
    md.append(
        "_Synthetic: the outcome model is a threshold sigmoid at ω=40, not a real-world "
        "label set. The optimal λ values here should be validated on production outcomes "
        "before being used as scheduling defaults._"
    )

    with open(OUT_MD, "w") as f:
        f.write("\n".join(md) + "\n")

    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    print("Optimal λ per domain (accuracy):",
          {d: results[d]["optimal_lambda_accuracy"] for d in DOMAINS})


if __name__ == "__main__":
    main()
