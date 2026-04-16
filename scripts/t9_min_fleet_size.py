"""
T9 — Minimum Viable Fleet Size for Vaccination

Question: Below what fleet size N does vaccination add no statistical value?

Model: With N agents, each making C calls/day, and attack rate lambda per 1,000
agent-days, daily attacks = N * C * (lambda/1000). With K unique attack signatures
in the universe, the birthday-paradox approximation for expected number of repeat
signatures after T days:

    E[repeats] ~ T * N * C * (N*C - 1) / (2 * K) * (lambda/1000)

For vaccination to be non-theater, E[repeats] >= 1 over a reasonable window.

Parameters:
  C = 100 calls/day/agent
  lambda = 2 attacks per 1,000 agent-days
  K = 10,000 unique attack signatures
  T = 30 days
"""

import json
import math
from pathlib import Path


def expected_repeats(N: int, C: int, lam: float, K: int, T: int) -> float:
    """Expected number of repeat attack signatures over T days."""
    # Daily exposure calls
    daily_calls = N * C
    # Birthday-paradox style collision expectation, scaled by attack rate
    # E[repeats] = T * daily_calls * (daily_calls - 1) / (2K) * (lambda/1000)
    return T * daily_calls * (daily_calls - 1) / (2.0 * K) * (lam / 1000.0)


def time_to_first_repeat(N: int, C: int, lam: float, K: int) -> float:
    """Solve for T such that E[repeats] = 1, given fleet size N."""
    daily_calls = N * C
    if daily_calls <= 1:
        return float("inf")
    denom = daily_calls * (daily_calls - 1) / (2.0 * K) * (lam / 1000.0)
    if denom <= 0:
        return float("inf")
    return 1.0 / denom


def min_fleet_size(C: int, lam: float, K: int, T: int, threshold: float = 1.0) -> int:
    """Smallest integer N such that E[repeats] >= threshold over T days."""
    # Solve quadratic: T * (N*C)^2 / (2K) * (lambda/1000) ~ threshold
    # Approximate: N^2 * C^2 = threshold * 2K * 1000 / (T * lambda)
    # N ~ sqrt(threshold * 2K * 1000 / (T * lambda)) / C
    # Then search +/- a few to be exact using discrete formula
    approx_N = math.sqrt(threshold * 2.0 * K * 1000.0 / (T * lam)) / C
    start = max(1, int(approx_N) - 5)
    for N in range(start, start + 10_000):
        if expected_repeats(N, C, lam, K, T) >= threshold:
            return N
    return -1  # not found in search window


def main() -> None:
    # Model parameters
    C = 100
    lam = 2.0
    K = 10_000
    T = 30
    threshold = 1.0

    n_min = min_fleet_size(C, lam, K, T, threshold)

    # Expected time to first repeat signature at various fleet sizes
    fleet_sizes = [10, 50, 100, 500, 1000, 5000]
    time_to_repeat = {}
    for N in fleet_sizes:
        t = time_to_first_repeat(N, C, lam, K)
        if math.isinf(t) or t > 365 * 100:
            time_to_repeat[str(N)] = "never (>100 years)"
        elif t > 365:
            time_to_repeat[str(N)] = f"{t/365:.1f} years ({t:.0f} days)"
        elif t > 30:
            time_to_repeat[str(N)] = f"{t:.0f} days"
        else:
            time_to_repeat[str(N)] = f"{t:.2f} days"

    # Also compute E[repeats] at those sizes over the 30-day window for context
    repeats_at_N = {str(N): round(expected_repeats(N, C, lam, K, T), 4) for N in fleet_sizes}

    interpretation = (
        f"Fleet sizes below N={n_min} yield fewer than 1 expected repeat attack "
        f"signature over a 30-day window, given {K:,} possible signatures, "
        f"{C} calls/agent/day, and {lam} attacks/1000 agent-days. Vaccination "
        f"relies on cross-agent signature reuse; when reuse is statistically "
        f"absent, immunization cache cannot be populated or queried against "
        f"a second occurrence within the operational horizon."
    )

    verdict = (
        f"Below N={n_min} fleet size, vaccination is theater — "
        f"attacks are too unique to repeat within 30 days. "
        f"Above N={n_min}, vaccination provides measurable protection "
        f"(expected repeats >= 1 per month)."
    )

    out = {
        "model": {
            "calls_per_agent_per_day": C,
            "attack_rate_per_1000_agent_days": lam,
            "unique_signature_universe": K,
            "operational_window_days": T,
            "repeat_threshold": threshold,
            "formula": "E[repeats] = T * N * C * (N*C - 1) / (2K) * (lambda/1000)",
        },
        "minimum_viable_fleet_size": n_min,
        "time_to_first_repeat_by_fleet_size": time_to_repeat,
        "expected_repeats_over_30_days_by_fleet_size": repeats_at_N,
        "interpretation": interpretation,
        "verdict": verdict,
    }

    out_path = Path("/Users/zsobrakpeter/core/research/results/min_fleet_size.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(out, f, indent=2)

    print(f"Minimum viable fleet size: N = {n_min}")
    print(f"Saved to: {out_path}")
    print("\nTime to first repeat signature:")
    for N, t in time_to_repeat.items():
        print(f"  N={N}: {t}  (E[repeats]/30d = {repeats_at_N[N]})")
    print(f"\nVerdict: {verdict}")


if __name__ == "__main__":
    main()
