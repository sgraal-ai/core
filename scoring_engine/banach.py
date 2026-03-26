from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class BanachResult:
    k_estimate: float
    contraction_guaranteed: bool
    convergence_steps: float
    fixed_point_estimate: float


def compute_banach(
    score_history: list[float],
    current_score: float,
    min_observations: int = 5,
) -> Optional[BanachResult]:
    """Banach Fixed-Point Theorem contraction mapping verification.

    k = median(|x_{i+1} - x_i| / |x_i - x_{i-1}| + ε)
    contraction_guaranteed when k < 1.0
    convergence_steps = log(0.01) / log(k)

    Args:
        score_history: past scores (oldest first)
        current_score: current score
        min_observations: minimum history (default 5)

    Returns:
        BanachResult or None if insufficient history
    """
    if len(score_history) < min_observations:
        return None

    try:
        all_scores = score_history + [current_score]
        n = len(all_scores)

        if n < 3:
            return None

        eps = 1e-8
        ratios = []

        for i in range(1, n - 1):
            d_prev = abs(all_scores[i] - all_scores[i - 1])
            d_next = abs(all_scores[i + 1] - all_scores[i])

            # Skip identical consecutive pairs
            if d_prev < eps:
                continue

            ratios.append(d_next / d_prev)

        # All pairs identical
        if not ratios:
            return BanachResult(
                k_estimate=0.0,
                contraction_guaranteed=True,
                convergence_steps=0.0,
                fixed_point_estimate=round(all_scores[-1], 4),
            )

        # Median of ratios
        ratios.sort()
        mid = len(ratios) // 2
        k = ratios[mid] if len(ratios) % 2 == 1 else (ratios[mid - 1] + ratios[mid]) / 2

        contraction = k < 1.0

        # Convergence steps: log(tolerance) / log(k)
        if 0 < k < 1.0:
            conv_steps = math.log(0.01) / math.log(k)
        else:
            conv_steps = 0.0

        # Fixed point estimate: last value (limit of contracting sequence)
        fp = round(all_scores[-1], 4)

        return BanachResult(
            k_estimate=round(k, 4),
            contraction_guaranteed=contraction,
            convergence_steps=round(conv_steps, 2),
            fixed_point_estimate=fp,
        )
    except Exception:
        return None
