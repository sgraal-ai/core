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


def _quantile(sorted_vals: list[float], p: float) -> float:
    """Linear interpolation quantile on sorted values."""
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    if n == 1:
        return sorted_vals[0]
    idx = p * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _estimate_alpha(changes: list[float]) -> float:
    """Estimate Lévy stability index α via McCulloch's quantile method.

    Uses the ratio of quantile ranges to estimate tail heaviness:
    ν_α = (Q_95 - Q_5) / (Q_75 - Q_25)

    For Gaussian (α=2): ν_α ≈ 2.44
    For Cauchy (α=1): ν_α ≈ 6.31
    Interpolate α from empirical ν_α.

    Falls back to Hill estimator when quantile method is degenerate.
    """
    abs_changes = sorted(abs(c) for c in changes if abs(c) > 1e-10)
    n = len(abs_changes)

    if n < 5:
        return 2.0  # default to Gaussian

    # McCulloch quantile method
    q05 = _quantile(abs_changes, 0.05)
    q25 = _quantile(abs_changes, 0.25)
    q75 = _quantile(abs_changes, 0.75)
    q95 = _quantile(abs_changes, 0.95)

    iqr = q75 - q25
    outer_range = q95 - q05

    if iqr > 1e-10:
        nu = outer_range / iqr
        # Interpolate α from ν_α:
        # ν_α=2.44 → α=2.0 (Gaussian), ν_α=6.31 → α=1.0 (Cauchy)
        # Linear interpolation: α = 2.0 - (ν - 2.44) / (6.31 - 2.44)
        alpha = 2.0 - (nu - 2.44) / (6.31 - 2.44)
        # Alpha must be in (0, 2] for Levy stable distributions
        alpha = max(0.1, min(2.0, alpha))
    else:
        # Degenerate IQR: fall back to Hill estimator
        sorted_desc = sorted(abs_changes, reverse=True)
        k = max(3, n // 3)
        threshold = sorted_desc[k - 1] if k <= n else sorted_desc[-1]
        if threshold < 1e-10:
            return 2.0
        hill_sum = sum(math.log(sorted_desc[i] / threshold) for i in range(k) if sorted_desc[i] > threshold)
        if hill_sum < 1e-10:
            return 2.0
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
    Estimates stability index α via McCulloch's quantile method (IQR ratio).
    Scale parameter c = IQR/2 (robust).

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

        # Scale parameter: IQR/2 robust estimate
        sorted_abs = sorted(abs(c) for c in changes)
        q25 = _quantile(sorted_abs, 0.25)
        q75 = _quantile(sorted_abs, 0.75)
        scale = round((q75 - q25) / 2.0, 4) if (q75 - q25) > 0 else 0.01

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
