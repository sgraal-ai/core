from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional


BOUNDED_STEPS = 10

# Default uniform transition probabilities (4 states)
_DEFAULT_TRANSITIONS = [
    [0.7, 0.2, 0.08, 0.02],   # SAFE → ...
    [0.2, 0.5, 0.25, 0.05],   # WARN → ...
    [0.05, 0.15, 0.5, 0.3],   # DEGRADED → ...
    [0.01, 0.04, 0.15, 0.8],  # CRITICAL → ...
]

# Heal transitions: after healing, better odds of improvement
_HEAL_TRANSITIONS = [
    [0.9, 0.08, 0.01, 0.01],
    [0.6, 0.3, 0.08, 0.02],
    [0.4, 0.35, 0.2, 0.05],
    [0.3, 0.3, 0.25, 0.15],
]

STATES = ["SAFE", "WARN", "DEGRADED", "CRITICAL"]
# State thresholds: SAFE=[0-25], WARN=[26-50], DEGRADED=[51-75], CRITICAL=[76-100]


@dataclass
class CTLResult:
    ef_recovery_possible: Optional[bool]
    ag_heal_works: Optional[bool]
    eg_stable_possible: Optional[bool]
    verified_states: int
    verification_time_ms: float
    bounded_steps: int
    ctl_formulas: list[str]


def _state_index(omega: float) -> int:
    if omega <= 25:
        return 0
    if omega <= 50:
        return 1
    if omega <= 75:
        return 2
    return 3


def _ef_check(
    start_state: int,
    transitions: list[list[float]],
    target_states: set[int],
    k: int = BOUNDED_STEPS,
) -> bool:
    """EF(φ): exists a path where φ holds eventually within k steps.

    BFS reachability: can we reach any target state from start?
    A state is reachable if transition probability > 0.01.
    """
    visited = set()
    frontier = {start_state}

    for _ in range(k):
        if frontier & target_states:
            return True
        next_frontier = set()
        for s in frontier:
            visited.add(s)
            for sp in range(4):
                if transitions[s][sp] > 0.01 and sp not in visited:
                    next_frontier.add(sp)
        frontier = next_frontier
        if not frontier:
            break

    return bool(frontier & target_states) or bool(visited & target_states)


def _ag_check(
    start_state: int,
    transitions: list[list[float]],
    heal_transitions: list[list[float]],
    k: int = BOUNDED_STEPS,
) -> bool:
    """AG(heal → AF(decrease)): on all paths, healing always eventually leads to improvement.

    Check: from every reachable state, after healing, can we reach a better state?
    """
    visited = set()
    frontier = {start_state}

    for _ in range(k):
        next_frontier = set()
        for s in frontier:
            visited.add(s)
            # After healing from state s, check if improvement is reachable
            better_states = set(range(s))  # states with lower index = better
            if s > 0:
                # Can heal transitions reach a better state?
                heal_reachable = False
                for sp in range(4):
                    if heal_transitions[s][sp] > 0.01 and sp < s:
                        heal_reachable = True
                        break
                if not heal_reachable:
                    return False  # found a state where healing doesn't help

            for sp in range(4):
                if transitions[s][sp] > 0.01 and sp not in visited:
                    next_frontier.add(sp)
        frontier = next_frontier
        if not frontier:
            break

    return True


def _eg_check(
    start_state: int,
    transitions: list[list[float]],
    target_states: set[int],
    k: int = BOUNDED_STEPS,
) -> bool:
    """EG(φ): exists a path where φ holds globally for k steps.

    Check: is there a path from start that stays within target_states for k steps?
    """
    if start_state not in target_states:
        return False

    # DFS: find a path of length k staying in target_states
    frontier = {start_state}

    for _ in range(k):
        next_frontier = set()
        for s in frontier:
            for sp in range(4):
                if transitions[s][sp] > 0.01 and sp in target_states:
                    next_frontier.add(sp)
        if not next_frontier:
            return False
        frontier = next_frontier

    return True


def compute_ctl_verification(
    omega_mem_final: float,
    hmm_transitions: Optional[list[list[float]]] = None,
    timeout_ms: float = 100.0,
) -> Optional[CTLResult]:
    """Computation Tree Logic verification for branching-time workflows.

    Bounded model checking with k=10 steps.

    Formulas:
    - EF(omega < 50): recovery is possible within 10 steps
    - AG(heal → AF(decrease)): healing always leads to improvement on all paths
    - EG(omega < 80): stable operation possible on some path for 10 steps

    Args:
        omega_mem_final: current omega score
        hmm_transitions: HMM transition matrix (4x4) or None for defaults
        timeout_ms: verification timeout in milliseconds (default 100)

    Returns:
        CTLResult or None on error
    """
    try:
        t_start = time.monotonic()

        state = _state_index(omega_mem_final)
        transitions = hmm_transitions if hmm_transitions and len(hmm_transitions) == 4 else _DEFAULT_TRANSITIONS
        verified_states = 0

        formulas = ["EF(omega<50)", "AG(heal->AF(decrease))", "EG(omega<80)"]

        # EF(omega < 50): can reach SAFE or WARN state
        ef_result = None
        elapsed = (time.monotonic() - t_start) * 1000
        if elapsed < timeout_ms:
            ef_result = _ef_check(state, transitions, {0, 1})
            verified_states += 4

        # AG(heal → AF(decrease)): healing convergence on all paths
        ag_result = None
        elapsed = (time.monotonic() - t_start) * 1000
        if elapsed < timeout_ms:
            ag_result = _ag_check(state, transitions, _HEAL_TRANSITIONS)
            verified_states += 4

        # EG(omega < 80): stable below CRITICAL on some path
        eg_result = None
        elapsed = (time.monotonic() - t_start) * 1000
        if elapsed < timeout_ms:
            eg_result = _eg_check(state, transitions, {0, 1, 2})
            verified_states += 4

        total_time = round((time.monotonic() - t_start) * 1000, 2)

        return CTLResult(
            ef_recovery_possible=ef_result,
            ag_heal_works=ag_result,
            eg_stable_possible=eg_result,
            verified_states=verified_states,
            verification_time_ms=total_time,
            bounded_steps=BOUNDED_STEPS,
            ctl_formulas=formulas,
        )
    except Exception:
        return None
