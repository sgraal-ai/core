from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class HawkesResult:
    current_lambda: float
    baseline_mu: float
    excited: bool
    burst_detected: bool


def compute_hawkes_intensity(
    update_times: list[float],
    current_time: float,
    mu: float = 0.1,
    alpha: float = 0.5,
    beta: float = 1.0,
) -> HawkesResult:
    """Compute Hawkes self-exciting process intensity at current_time.

    λ(t) = μ + Σᵢ α · exp(-β · (t - tᵢ))

    where:
        μ = baseline rate (background intensity)
        α = excitation parameter (how much each event excites)
        β = decay rate (how fast excitement fades)
        tᵢ = past event times

    When multiple memory entries are updated in quick succession,
    the intensity spikes — one update triggering more.

    Args:
        update_times: list of past update timestamps (days ago, 0 = now)
        current_time: current time reference (typically 0)
        mu: baseline intensity rate
        alpha: excitation magnitude per event
        beta: exponential decay rate of excitement

    Returns:
        HawkesResult with current intensity, baseline, and burst detection
    """
    if not update_times:
        return HawkesResult(
            current_lambda=mu,
            baseline_mu=mu,
            excited=False,
            burst_detected=False,
        )

    # Sum excitation from all past events
    excitation = 0.0
    for t_i in update_times:
        dt = current_time - t_i
        if dt >= 0:
            excitation += alpha * math.exp(-beta * dt)

    current_lambda = mu + excitation
    current_lambda = round(current_lambda, 4)

    excited = current_lambda > mu * 1.2  # >20% above baseline
    burst_detected = current_lambda > mu * 2.0  # >2× baseline

    return HawkesResult(
        current_lambda=current_lambda,
        baseline_mu=mu,
        excited=excited,
        burst_detected=burst_detected,
    )


def hawkes_from_entries(
    timestamp_age_days: list[float],
    mu: float = 0.1,
    alpha: float = 0.5,
    beta: float = 1.0,
) -> HawkesResult:
    """Convenience: compute Hawkes intensity from entry ages.

    Converts timestamp_age_days to event times relative to now (t=0).
    Recent entries (low age) contribute more excitation.
    """
    # Convert ages to event times: age=0 → just happened, age=30 → 30 days ago
    # We use negative times (past) relative to current_time=0
    update_times = [-age for age in timestamp_age_days]
    return compute_hawkes_intensity(update_times, current_time=0, mu=mu, alpha=alpha, beta=beta)
