from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class LyapunovExponentResult:
    lambda_estimate: float
    chaos_risk: bool
    stability_class: str      # "converging", "neutral", "diverging"
    divergence_rate: float    # exp(λ)


def compute_lyapunov_exponent(
    score_history: list[float],
    current_score: float,
    min_observations: int = 10,
    chaos_threshold: float = 0.1,
) -> Optional[LyapunovExponentResult]:
    """Lyapunov exponent finite-time approximation for chaos detection.

    λ = (1/N) · Σᵢ log(|x_{i+1} - x_i| / |x_i - x_{i-1}| + ε)

    λ < 0: converging (stable)
    λ ≈ 0: neutral (borderline)
    λ > 0: diverging (chaotic)

    Args:
        score_history: past omega_mem_final scores (oldest first)
        current_score: current omega_mem_final score
        min_observations: minimum history length (default 10)
        chaos_threshold: λ above this = chaos_risk (default 0.1)

    Returns:
        LyapunovExponentResult or None if insufficient history
    """
    if len(score_history) < min_observations:
        return None

    try:
        all_scores = score_history + [current_score]
        n = len(all_scores)

        if n < 3:
            return None

        eps = 1e-8
        log_sum = 0.0
        count = 0

        for i in range(1, n - 1):
            d_prev = abs(all_scores[i] - all_scores[i - 1])
            d_next = abs(all_scores[i + 1] - all_scores[i])

            ratio = (d_next + eps) / (d_prev + eps)
            log_sum += math.log(ratio)
            count += 1

        if count == 0:
            return None

        lam = log_sum / count

        # Classification
        if lam < -0.05:
            stability_class = "converging"
        elif lam <= chaos_threshold:
            stability_class = "neutral"
        else:
            stability_class = "diverging"

        chaos_risk = lam > chaos_threshold
        divergence_rate = round(math.exp(lam), 4)

        return LyapunovExponentResult(
            lambda_estimate=round(lam, 4),
            chaos_risk=chaos_risk,
            stability_class=stability_class,
            divergence_rate=divergence_rate,
        )
    except Exception:
        return None
