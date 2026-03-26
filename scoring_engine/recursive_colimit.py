from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RecursiveColimitResult:
    global_state: float
    state_velocity: float
    colimit_stable: bool
    h1_factor: float
    iteration: int


def compute_recursive_colimit(
    omega_scores: list[float],
    h1_rank: int = 0,
    previous_state: Optional[float] = None,
    iteration: int = 0,
    min_observed: Optional[float] = None,
    max_observed: Optional[float] = None,
) -> Optional[RecursiveColimitResult]:
    """Recursive Colimit (Category Theory) for global state computation.

    GlobalState(t) = normalize(mean(omega_i) * H1_factor)
    GlobalState(t+1) = normalize(GlobalState(t) * mean(omega_i))

    Args:
        omega_scores: list of per-entry omega contributions
        h1_rank: sheaf H1 rank from consistency_analysis (0 = consistent)
        previous_state: stored GlobalState from Redis (None = first call)
        iteration: colimit iteration count
        min_observed: stored min for normalization
        max_observed: stored max for normalization

    Returns:
        RecursiveColimitResult or None on error
    """
    if not omega_scores:
        return None

    try:
        eps = 1e-8
        mean_omega = sum(omega_scores) / len(omega_scores)

        # H1 factor: 1 when consistent (h1=0), lower when inconsistent
        h1_factor = max(0.0, 1.0 - h1_rank / 10.0)

        if previous_state is None:
            # First call: uninformed prior
            raw = mean_omega * h1_factor
            global_state = 0.5
            velocity = 0.0
            iteration = 0
        else:
            # Recursive update
            raw = previous_state * mean_omega * h1_factor
            iteration += 1

            # Normalize via min-max
            if min_observed is not None and max_observed is not None:
                _min = min(min_observed, raw)
                _max = max(max_observed, raw)
            else:
                _min = raw
                _max = raw

            rng = _max - _min + eps
            global_state = (raw - _min) / rng
            global_state = max(0.0, min(1.0, global_state))

            velocity = global_state - previous_state

        colimit_stable = abs(velocity) < 0.05 if previous_state is not None else True

        return RecursiveColimitResult(
            global_state=round(global_state, 4),
            state_velocity=round(velocity, 4),
            colimit_stable=colimit_stable,
            h1_factor=round(h1_factor, 4),
            iteration=iteration,
        )
    except Exception:
        return None
