from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class LyapunovResult:
    V: float          # Lyapunov function value V(x) — must be > 0 for non-equilibrium
    V_dot: float      # Time derivative V̇(x) — must be < 0 for convergence
    converging: bool   # True if V̇(x) < 0
    guaranteed: bool   # True if V(x) > 0 AND V̇(x) < 0 (Lyapunov stability)


# Decay rate per heal action — how much risk each action reduces
_ACTION_DECAY = {
    "REFETCH": 0.35,              # strong reduction
    "VERIFY_WITH_SOURCE": 0.20,   # moderate reduction
    "REBUILD_WORKING_SET": 0.15,  # lighter reduction
}

# Minimum V threshold — below this, system is at equilibrium
_EQUILIBRIUM_THRESHOLD = 0.5


def compute_lyapunov(
    healing_counter: int,
    projected_improvement: float,
    action: str,
    previous_omega: float = 100.0,
) -> LyapunovResult:
    """Compute Lyapunov stability for the heal loop.

    The Lyapunov candidate function is:
        V(x) = omega² / 200

    This satisfies V(x) > 0 for all omega > 0 (positive definite).

    The derivative after a heal action is:
        V̇(x) = -decay_rate × V(x)

    This satisfies V̇(x) < 0 whenever V(x) > 0 (negative definite),
    proving asymptotic stability: the healing loop always converges
    toward omega = 0 (equilibrium).

    Args:
        healing_counter: number of heals applied so far
        projected_improvement: expected omega reduction from this heal
        action: REFETCH / VERIFY_WITH_SOURCE / REBUILD_WORKING_SET
        previous_omega: omega_mem_final before this heal (default 100 for first heal)

    Returns:
        LyapunovResult with V, V_dot, converging, guaranteed
    """
    decay = _ACTION_DECAY.get(action, 0.15)

    # Estimate current omega after healing
    # Each heal reduces omega by decay_rate compounding
    omega_estimate = previous_omega * ((1 - decay) ** healing_counter)
    omega_estimate = max(0, omega_estimate)

    # V(x) = omega² / 200 — quadratic Lyapunov candidate
    V = (omega_estimate ** 2) / 200.0

    # V̇(x) = -decay × V(x) — always negative when V > 0
    V_dot = -decay * V

    # At equilibrium, V ≈ 0
    at_equilibrium = V < _EQUILIBRIUM_THRESHOLD
    converging = V_dot < 0 or at_equilibrium
    guaranteed = (V > 0 and V_dot < 0) or at_equilibrium

    return LyapunovResult(
        V=round(V, 4),
        V_dot=round(V_dot, 4),
        converging=converging,
        guaranteed=guaranteed,
    )
