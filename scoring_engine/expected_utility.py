from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

ACTIONS = ["USE_MEMORY", "WARN", "ASK_USER", "BLOCK"]
VALUES = {"USE_MEMORY": 1.0, "WARN": 0.8, "ASK_USER": 0.6, "BLOCK": 0.5}
COSTS = {"USE_MEMORY": 2.0, "WARN": 1.0, "ASK_USER": 0.5, "BLOCK": 0.3}
PRIOR_SUCCESS = {"USE_MEMORY": 0.7, "WARN": 0.8, "ASK_USER": 0.9, "BLOCK": 0.95}

@dataclass
class ExpectedUtilityResult:
    utilities: dict[str, float]
    optimal_action: str
    utility_margin: float
    utility_using_prior_probabilities: bool

def compute_expected_utility(q_values: Optional[list[float]] = None, learning_episodes: int = 0) -> ExpectedUtilityResult:
    using_prior = q_values is None or learning_episodes < 10
    utilities = {}
    for i, a in enumerate(ACTIONS):
        if not using_prior and q_values:
            q_max = max(q_values) if max(q_values) > 0 else 1.0
            p_success = min(1.0, max(0.1, 0.5 + q_values[i] / (2 * max(q_max, 0.01))))
        else:
            p_success = PRIOR_SUCCESS[a]
        eu = p_success * VALUES[a] - (1.0 - p_success) * COSTS[a]
        utilities[a] = round(eu, 4)
    best = max(utilities, key=utilities.get)
    sorted_vals = sorted(utilities.values(), reverse=True)
    margin = round(sorted_vals[0] - sorted_vals[1], 4) if len(sorted_vals) > 1 else 0.0
    return ExpectedUtilityResult(utilities=utilities, optimal_action=best, utility_margin=margin, utility_using_prior_probabilities=using_prior)
