#!/usr/bin/env python3
"""
Research Task #446: Omega vs outcome correlation.

Measures Spearman correlation between omega_mem_final and outcome (success/failure).
Uses corpus test cases as synthetic outcomes when insufficient real data exists.
"""
import sys, os, math, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def _entry(**overrides):
    defaults = {
        "id": "oc_001", "content": "Test", "type": "semantic",
        "timestamp_age_days": 5, "source_trust": 0.85, "source_conflict": 0.1,
        "downstream_count": 3,
    }
    defaults.update(overrides)
    return defaults


def spearman_correlation(x, y):
    """Compute Spearman rank correlation coefficient and approximate p-value."""
    n = len(x)
    if n < 3:
        return 0.0, 1.0

    def rank(vals):
        indexed = sorted(enumerate(vals), key=lambda p: p[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                ranks[indexed[k][0]] = avg_rank
            i = j + 1
        return ranks

    rx = rank(x)
    ry = rank(y)

    d_sq = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    rho = 1 - 6 * d_sq / (n * (n * n - 1))

    # Approximate p-value using t-distribution approximation
    if abs(rho) >= 1.0:
        p_value = 0.0
    else:
        t = rho * math.sqrt((n - 2) / (1 - rho * rho))
        # Two-tailed p-value approximation
        df = n - 2
        p_value = 2 * (1 - _t_cdf(abs(t), df))

    return round(rho, 4), round(p_value, 6)


def _t_cdf(t, df):
    """Approximate t-distribution CDF using normal approximation for df > 30."""
    if df > 30:
        return _normal_cdf(t)
    # Rough approximation for smaller df
    x = df / (df + t * t)
    return 1 - 0.5 * _incomplete_beta(df / 2, 0.5, x)


def _normal_cdf(x):
    """Approximate standard normal CDF."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _incomplete_beta(a, b, x):
    """Very rough incomplete beta approximation."""
    # Use simple numerical integration
    n_steps = 200
    total = 0.0
    dx = x / n_steps
    for i in range(n_steps):
        t = (i + 0.5) * dx
        if t > 0 and t < 1:
            total += t ** (a - 1) * (1 - t) ** (b - 1) * dx
    # Normalize by beta function
    beta = math.gamma(a) * math.gamma(b) / math.gamma(a + b)
    return total / beta if beta > 0 else 0


def generate_synthetic_outcomes():
    """Generate outcome data from diverse memory states covering the omega spectrum."""
    import random
    rng = random.Random(46)

    cases = []

    # Safe cases (should succeed) — low omega expected
    for i in range(40):
        trust = rng.uniform(0.8, 0.99)
        age = rng.uniform(0.1, 10)
        conflict = rng.uniform(0.01, 0.1)
        dc = rng.randint(1, 5)
        cases.append({
            "entries": [_entry(id=f"safe_{i}", timestamp_age_days=age,
                               source_trust=trust, source_conflict=conflict,
                               downstream_count=dc)],
            "action_type": "informational",
            "domain": "general",
            "expected_outcome": 1,  # success
        })

    # Moderate cases (mixed outcomes)
    for i in range(30):
        trust = rng.uniform(0.4, 0.7)
        age = rng.uniform(10, 100)
        conflict = rng.uniform(0.1, 0.4)
        dc = rng.randint(3, 20)
        cases.append({
            "entries": [_entry(id=f"mod_{i}", timestamp_age_days=age,
                               source_trust=trust, source_conflict=conflict,
                               downstream_count=dc)],
            "action_type": "reversible",
            "domain": rng.choice(["general", "coding", "customer_support"]),
            "expected_outcome": rng.choice([0, 1, 1]),  # mostly success
        })

    # Risky cases (should fail) — high omega expected
    for i in range(30):
        trust = rng.uniform(0.1, 0.4)
        age = rng.uniform(100, 500)
        conflict = rng.uniform(0.4, 0.9)
        dc = rng.randint(10, 60)
        cases.append({
            "entries": [_entry(id=f"risky_{i}", timestamp_age_days=age,
                               source_trust=trust, source_conflict=conflict,
                               downstream_count=dc)],
            "action_type": rng.choice(["irreversible", "destructive"]),
            "domain": rng.choice(["fintech", "medical", "legal"]),
            "expected_outcome": 0,  # failure
        })

    # Very risky cases — BLOCK expected
    for i in range(20):
        cases.append({
            "entries": [
                _entry(id=f"vr_{i}_a", timestamp_age_days=rng.uniform(200, 500),
                       source_trust=rng.uniform(0.05, 0.2), source_conflict=rng.uniform(0.7, 0.95),
                       downstream_count=rng.randint(20, 80)),
                _entry(id=f"vr_{i}_b", timestamp_age_days=rng.uniform(100, 300),
                       source_trust=rng.uniform(0.1, 0.3), source_conflict=rng.uniform(0.5, 0.8),
                       downstream_count=rng.randint(10, 40)),
            ],
            "action_type": "destructive",
            "domain": "medical",
            "expected_outcome": 0,  # failure
        })

    return cases


def main():
    print("=" * 60)
    print("  Research Task #446: Omega vs Outcome Correlation")
    print("=" * 60)
    print()

    cases = generate_synthetic_outcomes()
    print(f"Generated {len(cases)} synthetic outcome cases")
    print()

    omegas = []
    outcomes = []
    actions = []

    for i, case in enumerate(cases):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": case["entries"],
            "action_type": case["action_type"],
            "domain": case["domain"],
        })
        if r.status_code != 200:
            continue
        j = r.json()
        omega = j.get("omega_mem_final", 0)
        omegas.append(omega)
        outcomes.append(case["expected_outcome"])
        actions.append(j.get("recommended_action", "USE_MEMORY"))

        if (i + 1) % 30 == 0:
            print(f"  Processed {i + 1}/{len(cases)} cases...")

    n = len(omegas)
    print(f"\nTotal scored: {n} cases")
    print()

    # Compute correlation
    rho, p_value = spearman_correlation(omegas, outcomes)

    # Distribution stats
    success_omegas = [o for o, out in zip(omegas, outcomes) if out == 1]
    failure_omegas = [o for o, out in zip(omegas, outcomes) if out == 0]

    success_mean = sum(success_omegas) / max(len(success_omegas), 1)
    failure_mean = sum(failure_omegas) / max(len(failure_omegas), 1)
    success_median = sorted(success_omegas)[len(success_omegas) // 2] if success_omegas else 0
    failure_median = sorted(failure_omegas)[len(failure_omegas) // 2] if failure_omegas else 0

    # Interpretation
    if rho < -0.5:
        interpretation = "Strong negative correlation — higher omega reliably predicts failure. Scoring is well-calibrated."
    elif rho < -0.3:
        interpretation = "Moderate negative correlation — omega is a useful predictor but not perfectly calibrated."
    elif rho < -0.1:
        interpretation = "Weak negative correlation — omega has some predictive value but needs calibration improvement."
    elif rho > 0.1:
        interpretation = "WARNING: Positive correlation — higher omega predicts SUCCESS. Scoring may be inverted."
    else:
        interpretation = "No significant correlation — omega does not predict outcome. Scoring needs fundamental review."

    # Action accuracy
    true_positives = sum(1 for a, o in zip(actions, outcomes) if a == "BLOCK" and o == 0)
    true_negatives = sum(1 for a, o in zip(actions, outcomes) if a == "USE_MEMORY" and o == 1)
    false_positives = sum(1 for a, o in zip(actions, outcomes) if a == "BLOCK" and o == 1)
    false_negatives = sum(1 for a, o in zip(actions, outcomes) if a == "USE_MEMORY" and o == 0)
    # WARN and ASK_USER
    warn_success = sum(1 for a, o in zip(actions, outcomes) if a in ("WARN", "ASK_USER") and o == 1)
    warn_failure = sum(1 for a, o in zip(actions, outcomes) if a in ("WARN", "ASK_USER") and o == 0)

    accuracy = (true_positives + true_negatives) / max(n, 1)

    result = {
        "spearman_rho": rho,
        "p_value": p_value,
        "n_samples": n,
        "interpretation": interpretation,
        "success_omega_mean": round(success_mean, 1),
        "success_omega_median": round(success_median, 1),
        "failure_omega_mean": round(failure_mean, 1),
        "failure_omega_median": round(failure_median, 1),
        "n_success": len(success_omegas),
        "n_failure": len(failure_omegas),
        "action_accuracy": round(accuracy, 3),
        "confusion_matrix": {
            "true_positive_block_failure": true_positives,
            "true_negative_use_success": true_negatives,
            "false_positive_block_success": false_positives,
            "false_negative_use_failure": false_negatives,
            "warn_on_success": warn_success,
            "warn_on_failure": warn_failure,
        },
    }

    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print()
    print(f"  Spearman ρ:  {rho:+.4f}  (p={p_value:.6f})")
    print(f"  Samples:     {n}")
    print(f"  Interpretation: {interpretation}")
    print()
    print(f"  Success cases (outcome=1):  mean omega = {success_mean:.1f}, median = {success_median:.1f}, n = {len(success_omegas)}")
    print(f"  Failure cases (outcome=0):  mean omega = {failure_mean:.1f}, median = {failure_median:.1f}, n = {len(failure_omegas)}")
    print(f"  Separation:  {failure_mean - success_mean:+.1f} points (failure - success)")
    print()
    print(f"  Action accuracy: {accuracy*100:.1f}%")
    print(f"  Confusion matrix:")
    print(f"    BLOCK on failure (TP):     {true_positives}")
    print(f"    USE_MEMORY on success (TN): {true_negatives}")
    print(f"    BLOCK on success (FP):     {false_positives}")
    print(f"    USE_MEMORY on failure (FN): {false_negatives}")
    print(f"    WARN on success:           {warn_success}")
    print(f"    WARN on failure:           {warn_failure}")
    print()

    # ASCII histogram
    print("  Omega distribution:")
    bins = [(0, 10), (10, 20), (20, 30), (30, 40), (40, 50), (50, 60), (60, 70), (70, 80), (80, 90), (90, 100)]
    for lo, hi in bins:
        s_count = sum(1 for o in success_omegas if lo <= o < hi)
        f_count = sum(1 for o in failure_omegas if lo <= o < hi)
        s_bar = "+" * s_count
        f_bar = "x" * f_count
        print(f"    {lo:3d}-{hi:3d}  {s_bar}{f_bar}  (s={s_count} f={f_count})")
    print("    + = success, x = failure")
    print()

    with open("/tmp/omega_outcome_results.json", "w") as f:
        json.dump(result, f, indent=2)
    print("  Detailed results: /tmp/omega_outcome_results.json")


if __name__ == "__main__":
    main()
