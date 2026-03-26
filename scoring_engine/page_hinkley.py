from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PageHinkleyResult:
    ph_statistic: float
    alert: bool
    change_magnitude: float
    steps_since_change: int
    running_mean: float
    delta_used: float
    lambda_used: float


def compute_page_hinkley(
    score_history: list[float],
    current_score: float,
    delta: float = 0.005,
    lam: float = 50.0,
    min_observations: int = 5,
) -> Optional[PageHinkleyResult]:
    """Page-Hinkley online change detection.

    mₜ = mₜ₋₁ + (xₜ - μ̂ₜ - δ)
    PHₜ = mₜ - min_{i≤t} mᵢ
    Alert when PHₜ > λ

    Detects the exact step where drift became permanent.
    Complementary to CUSUM (sustained drift) and BOCPD (regime change).

    Args:
        score_history: past omega_mem_final scores (oldest first)
        current_score: current omega_mem_final score
        delta: allowable magnitude of change (default 0.005)
        lam: detection threshold λ (default 50.0)
        min_observations: minimum history length (default 5)

    Returns:
        PageHinkleyResult or None if insufficient history
    """
    if len(score_history) < min_observations:
        return None

    try:
        all_scores = score_history + [current_score]
        n = len(all_scores)

        # Running Page-Hinkley computation
        running_sum = 0.0
        running_mean = 0.0
        min_m = 0.0
        m_t = 0.0
        ph_t = 0.0
        alert = False
        change_step = -1

        for t in range(n):
            # Update running mean: μ̂ₜ = (1/(t+1)) Σ xᵢ
            running_mean = (running_mean * t + all_scores[t]) / (t + 1)

            # mₜ = mₜ₋₁ + (xₜ - μ̂ₜ - δ)
            m_t = m_t + (all_scores[t] - running_mean - delta)

            # Track minimum
            if m_t < min_m:
                min_m = m_t

            # PHₜ = mₜ - min_{i≤t} mᵢ
            ph_t = m_t - min_m

            # Check alert
            if ph_t > lam and not alert:
                alert = True
                change_step = t

        # Steps since change
        if alert and change_step >= 0:
            steps_since = n - 1 - change_step
        else:
            steps_since = 0

        # Change magnitude: difference between pre/post change means
        if alert and change_step > 0 and change_step < n - 1:
            pre_mean = sum(all_scores[:change_step]) / change_step
            post_mean = sum(all_scores[change_step:]) / (n - change_step)
            change_mag = abs(post_mean - pre_mean)
        else:
            change_mag = 0.0

        return PageHinkleyResult(
            ph_statistic=round(ph_t, 4),
            alert=alert,
            change_magnitude=round(change_mag, 4),
            steps_since_change=steps_since,
            running_mean=round(running_mean, 4),
            delta_used=delta,
            lambda_used=lam,
        )
    except Exception:
        return None
