from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class LevyFlightResult:
    alpha: float                    # stability index (0-2, lower = heavier tail)
    scale: float                    # scale parameter
    heavy_tail_risk: bool           # true when alpha < 1.5
    extreme_event_probability: float  # P(|X| > 3σ)
    tail_index: str                 # "light", "moderate", "heavy", "extreme"


def _estimate_alpha(changes: list[float]) -> float:
    """Estimate Lévy stability index α via Hill estimator on absolute changes.

    α close to 2 = Gaussian (light tails)
    α close to 1 = Cauchy (heavy tails)
    α < 1 = extremely heavy tails

    Hill estimator: 1/α ≈ (1/k) Σ log(X_(n-i) / X_(n-k)) for top-k order statistics.
    """
    abs_changes = sorted([abs(c) for c in changes if abs(c) > 1e-10], reverse=True)
    n = len(abs_changes)

    if n < 5:
        return 2.0  # default to Gaussian

    # Use top 30% as tail for Hill estimator
    k = max(3, n // 3)
    threshold = abs_changes[k - 1]

    if threshold < 1e-10:
        return 2.0

    hill_sum = sum(math.log(abs_changes[i] / threshold) for i in range(k))

    if hill_sum < 1e-10:
        return 2.0

    # Hill estimator gives tail index ξ = 1/α
    xi = hill_sum / k
    alpha = 1.0 / xi if xi > 0.01 else 2.0

    # Clamp to valid Lévy stable range (0, 2]
    return max(0.1, min(2.0, alpha))


def compute_levy_flight(
    score_history: list[float],
    current_score: float,
    min_observations: int = 10,
) -> Optional[LevyFlightResult]:
    """Lévy Flight tail analysis for extreme event detection.

    Models score changes as draws from a Lévy α-stable distribution.
    Estimates the stability index α to quantify tail heaviness.

    α = 2: Gaussian (light tails, normal volatility)
    α ∈ [1.5, 2): moderate tails
    α ∈ [1, 1.5): heavy tails (frequent large jumps)
    α < 1: extreme tails (very frequent extreme events)

    Args:
        score_history: past omega_mem_final scores (oldest first)
        current_score: current omega_mem_final score
        min_observations: minimum history length (default 10)

    Returns:
        LevyFlightResult or None if insufficient history
    """
    if len(score_history) < min_observations:
        return None

    try:
        all_scores = score_history + [current_score]
        changes = [all_scores[i + 1] - all_scores[i] for i in range(len(all_scores) - 1)]
        n = len(changes)

        if n < 3:
            return None

        # Estimate stability index α
        alpha = _estimate_alpha(changes)

        # Scale parameter: MAD-based (robust)
        sorted_abs = sorted(abs(c) for c in changes)
        median_abs = sorted_abs[len(sorted_abs) // 2]
        scale = round(median_abs * 1.4826, 4) if median_abs > 0 else 0.01

        # Tail classification
        if alpha >= 1.8:
            tail_index = "light"
        elif alpha >= 1.5:
            tail_index = "moderate"
        elif alpha >= 1.0:
            tail_index = "heavy"
        else:
            tail_index = "extreme"

        heavy_tail_risk = alpha < 1.5

        # Extreme event probability: P(|X| > 3σ)
        # For Lévy stable: P(|X| > x) ~ x^(-α) for large x
        # Approximate using empirical exceedance
        sigma = scale if scale > 0 else 1e-6
        threshold_3s = 3 * sigma
        n_extreme = sum(1 for c in changes if abs(c) > threshold_3s)
        extreme_prob = round(n_extreme / max(n, 1), 4)
        extreme_prob = min(1.0, max(0.0, extreme_prob))

        return LevyFlightResult(
            alpha=round(alpha, 4),
            scale=scale,
            heavy_tail_risk=heavy_tail_risk,
            extreme_event_probability=extreme_prob,
            tail_index=tail_index,
        )
    except Exception:
        return None
