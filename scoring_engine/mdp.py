from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


STATES = ["SAFE", "WARN", "DEGRADED", "CRITICAL"]
ACTIONS = ["WAIT", "SOFT_HEAL", "FULL_HEAL", "EMERGENCY_HEAL"]
N_STATES = 4
N_ACTIONS = 4
GAMMA = 0.9


@dataclass
class MDPResult:
    optimal_action: str
    expected_value: float
    action_values: dict[str, float]
    state: str
    confidence: float


def _state_index(omega: float) -> int:
    """Discretize omega_mem_final into state index."""
    if omega <= 25:
        return 0  # SAFE
    if omega <= 50:
        return 1  # WARN
    if omega <= 75:
        return 2  # DEGRADED
    return 3  # CRITICAL


# Reward matrix R[state][action]
_REWARDS = [
    # SAFE:     WAIT   SOFT    FULL    EMERGENCY
    [1.0,       0.4,    0.7,    0.7],
    # WARN:     WAIT   SOFT    FULL    EMERGENCY
    [0.2,       0.4,    0.7,    0.7],
    # DEGRADED: WAIT   SOFT    FULL    EMERGENCY
    [-0.5,      0.4,    0.7,    0.7],
    # CRITICAL: WAIT   SOFT    FULL    EMERGENCY
    [-2.0,      0.4,    0.7,    0.7],
]


def _default_transitions() -> list[list[list[list[float]]]]:
    """Default transition probabilities P[s][a][s'] with uniform fallback.

    Structure: P[state][action] = [prob_SAFE, prob_WARN, prob_DEGRADED, prob_CRITICAL]

    Heuristic defaults:
    - WAIT: likely stay in same state or drift worse
    - SOFT_HEAL: moderate chance of improvement
    - FULL_HEAL: high chance of improvement
    - EMERGENCY_HEAL: very high chance of reaching SAFE
    """
    P = [[None] * N_ACTIONS for _ in range(N_STATES)]

    # SAFE state
    P[0][0] = [0.8, 0.15, 0.04, 0.01]  # WAIT: mostly stay SAFE
    P[0][1] = [0.9, 0.08, 0.01, 0.01]  # SOFT_HEAL
    P[0][2] = [0.95, 0.04, 0.005, 0.005]  # FULL_HEAL
    P[0][3] = [0.98, 0.01, 0.005, 0.005]  # EMERGENCY

    # WARN state
    P[1][0] = [0.2, 0.5, 0.25, 0.05]  # WAIT: may improve or degrade
    P[1][1] = [0.5, 0.35, 0.1, 0.05]  # SOFT_HEAL
    P[1][2] = [0.7, 0.2, 0.08, 0.02]  # FULL_HEAL
    P[1][3] = [0.85, 0.1, 0.03, 0.02]  # EMERGENCY

    # DEGRADED state
    P[2][0] = [0.05, 0.15, 0.5, 0.3]  # WAIT: likely stay or worsen
    P[2][1] = [0.2, 0.35, 0.35, 0.1]  # SOFT_HEAL
    P[2][2] = [0.5, 0.3, 0.15, 0.05]  # FULL_HEAL
    P[2][3] = [0.7, 0.2, 0.08, 0.02]  # EMERGENCY

    # CRITICAL state
    P[3][0] = [0.01, 0.04, 0.15, 0.8]  # WAIT: mostly stay CRITICAL
    P[3][1] = [0.1, 0.2, 0.3, 0.4]  # SOFT_HEAL
    P[3][2] = [0.35, 0.3, 0.2, 0.15]  # FULL_HEAL
    P[3][3] = [0.6, 0.25, 0.1, 0.05]  # EMERGENCY

    return P


def _value_iteration(
    R: list[list[float]],
    P: list[list[list[float]]],
    gamma: float = GAMMA,
    max_iter: int = 100,
    threshold: float = 1e-4,
) -> tuple[list[float], list[int]]:
    """Value iteration: V*(s) = max_a [R(s,a) + γ · Σ P(s'|s,a) · V*(s')].

    Returns (V_star, policy) where policy[s] = optimal action index.
    """
    V = [0.0] * N_STATES

    for _ in range(max_iter):
        V_new = [0.0] * N_STATES
        for s in range(N_STATES):
            best = -float("inf")
            for a in range(N_ACTIONS):
                q = R[s][a] + gamma * sum(P[s][a][sp] * V[sp] for sp in range(N_STATES))
                if q > best:
                    best = q
            V_new[s] = best

        # Check convergence
        delta = max(abs(V_new[s] - V[s]) for s in range(N_STATES))
        V = V_new
        if delta < threshold:
            break

    # Extract policy
    policy = [0] * N_STATES
    for s in range(N_STATES):
        best_a = 0
        best_q = -float("inf")
        for a in range(N_ACTIONS):
            q = R[s][a] + gamma * sum(P[s][a][sp] * V[sp] for sp in range(N_STATES))
            if q > best_q:
                best_q = q
                best_a = a
        policy[s] = best_a

    return V, policy


def compute_mdp(
    omega_mem_final: float,
    transition_data: Optional[dict] = None,
) -> Optional[MDPResult]:
    """Compute MDP optimal healing strategy.

    Args:
        omega_mem_final: current omega score
        transition_data: optional learned transitions from Redis
            {"transitions": P[s][a][s'], "n_outcomes": int}

    Returns:
        MDPResult or None on error
    """
    try:
        state_idx = _state_index(omega_mem_final)
        state = STATES[state_idx]

        # Use learned transitions or defaults
        if transition_data and transition_data.get("transitions"):
            P = transition_data["transitions"]
            n_outcomes = transition_data.get("n_outcomes", 0)
            confidence = min(1.0, n_outcomes / 100.0)
        else:
            P = _default_transitions()
            confidence = 0.1

        # Value iteration
        V, policy = _value_iteration(_REWARDS, P)

        # Action values for current state
        action_vals = {}
        for a in range(N_ACTIONS):
            q = _REWARDS[state_idx][a] + GAMMA * sum(
                P[state_idx][a][sp] * V[sp] for sp in range(N_STATES)
            )
            action_vals[ACTIONS[a]] = round(q, 4)

        optimal_idx = policy[state_idx]

        return MDPResult(
            optimal_action=ACTIONS[optimal_idx],
            expected_value=round(V[state_idx], 4),
            action_values=action_vals,
            state=state,
            confidence=round(confidence, 2),
        )
    except Exception:
        return None
