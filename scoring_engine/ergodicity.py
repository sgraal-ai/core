from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ErgodicityResult:
    time_average: float
    ensemble_average: float
    delta: float
    ergodic: bool
    interpretation: str


def compute_ergodicity(
    score_history: list[float],
    current_score: float,
    component_scores: list[float],
    ergodic_threshold: float = 5.0,
    min_observations: int = 5,
) -> Optional[ErgodicityResult]:
    """Ergodicity measure: time average vs ensemble average.

    Delta = |<X>_time - <X>_ensemble|
    ergodic when Delta < threshold.

    <X>_time = mean of score_history (temporal trajectory of single agent)
    <X>_ensemble = mean of component_scores (cross-sectional snapshot)

    Args:
        score_history: past omega scores (time average source)
        current_score: current omega score
        component_scores: component breakdown values (ensemble average source)
        ergodic_threshold: delta below this = ergodic (default 5.0)
        min_observations: minimum history (default 5)

    Returns:
        ErgodicityResult or None if insufficient data
    """
    if len(score_history) < min_observations:
        return None

    try:
        # Time average: mean of historical omega scores
        all_scores = score_history + [current_score]
        time_avg = sum(all_scores) / len(all_scores)

        # Ensemble average: mean of current component scores
        if component_scores:
            ensemble_avg = sum(component_scores) / len(component_scores)
        else:
            ensemble_avg = current_score

        delta = abs(time_avg - ensemble_avg)
        ergodic = delta < ergodic_threshold

        if ergodic:
            interpretation = "ergodic — time and ensemble averages agree, system is well-mixed"
        elif delta < ergodic_threshold * 2:
            interpretation = "weakly non-ergodic — moderate divergence between time and ensemble"
        else:
            interpretation = "non-ergodic — significant gap, history-dependent behavior"

        return ErgodicityResult(
            time_average=round(time_avg, 4),
            ensemble_average=round(ensemble_avg, 4),
            delta=round(delta, 4),
            ergodic=ergodic,
            interpretation=interpretation,
        )
    except Exception:
        return None
