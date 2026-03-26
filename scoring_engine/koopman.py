from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class KoopmanResult:
    eigenvalues: list[float]
    dominant_mode: str          # "stable", "oscillating", "growing"
    prediction_5: float         # predicted omega 5 steps ahead
    stable: bool                # all |eigenvalues| <= 1.0


def _solve_lstsq_1d(x: list[float], y: list[float]) -> float:
    """Solve y = a*x via least squares: a = (x^T y) / (x^T x)."""
    n = len(x)
    if n == 0:
        return 0.0
    xy = sum(x[i] * y[i] for i in range(n))
    xx = sum(x[i] * x[i] for i in range(n))
    if xx < 1e-12:
        return 0.0
    return xy / xx


def compute_koopman(
    score_history: list[float],
    current_score: float,
    min_observations: int = 10,
) -> Optional[KoopmanResult]:
    """Koopman operator via Dynamic Mode Decomposition (1D).

    K_approx via least squares: x_{t+1} = K * x_t
    For 1D time series: K is a scalar (autoregressive coefficient).

    Eigenvalue = K itself in 1D.
    stable when |K| <= 1.0.

    Args:
        score_history: past omega scores (oldest first)
        current_score: current score
        min_observations: minimum history (default 10)

    Returns:
        KoopmanResult or None if insufficient history
    """
    if len(score_history) < min_observations:
        return None

    try:
        all_scores = score_history + [current_score]
        n = len(all_scores)

        # X = [x_0, x_1, ..., x_{n-2}], X' = [x_1, x_2, ..., x_{n-1}]
        X = all_scores[:-1]
        X_prime = all_scores[1:]

        # K = lstsq(X, X') — 1D scalar
        K = _solve_lstsq_1d(X, X_prime)

        eigenvalues = [round(K, 4)]
        stable = abs(K) <= 1.0

        # Dominant mode classification
        if abs(K) < 0.95:
            dominant_mode = "stable"
        elif abs(K) <= 1.05:
            dominant_mode = "oscillating"
        else:
            dominant_mode = "growing"

        # Prediction 5 steps ahead: x_{t+5} = K^5 * x_t
        pred_5 = current_score * (K ** 5)
        pred_5 = round(max(0, min(100, pred_5)), 2)

        return KoopmanResult(
            eigenvalues=eigenvalues,
            dominant_mode=dominant_mode,
            prediction_5=pred_5,
            stable=stable,
        )
    except Exception:
        return None
