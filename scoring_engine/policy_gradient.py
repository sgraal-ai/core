from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

ACTIONS = ["USE_MEMORY", "WARN", "ASK_USER", "BLOCK"]


@dataclass
class PolicyGradientResult:
    action_probabilities: dict[str, float]
    advantage: float
    temperature: float
    policy_entropy: float
    exploration_mode: bool
    best_action: str


def _softmax(values: list[float], temperature: float) -> list[float]:
    """Softmax with temperature: p_i = exp(v_i/τ) / Σ exp(v_j/τ)."""
    tau = max(temperature, 0.01)
    scaled = [v / tau for v in values]
    max_v = max(scaled)
    exps = [math.exp(v - max_v) for v in scaled]
    total = sum(exps) or 1.0
    return [e / total for e in exps]


def _entropy(probs: list[float]) -> float:
    """Shannon entropy H = -Σ p·log(p)."""
    return -sum(p * math.log(p + 1e-10) for p in probs if p > 0)


def compute_policy_gradient(
    q_values: list[float],
    current_action_idx: int,
    temperature: float = 1.0,
) -> PolicyGradientResult:
    """Policy gradient with advantage function.

    ∇_θ J = E[∇_θ log π_θ(a|s) · A(s,a)]
    A(s,a) = Q(s,a) - V(s)
    V(s) = max_a Q(s,a) as baseline
    π_θ(a|s) = exp(Q(s,a)/τ) / Σ exp(Q(s,a)/τ)

    Args:
        q_values: Q-values for [USE_MEMORY, WARN, ASK_USER, BLOCK]
        current_action_idx: index of the action chosen by RL-01
        temperature: softmax temperature τ (default 1.0)

    Returns:
        PolicyGradientResult
    """
    if len(q_values) != 4:
        q_values = [0.0, 0.0, 0.0, 0.0]

    # Softmax policy
    probs = _softmax(q_values, temperature)

    # Value baseline: V(s) = max_a Q(s,a)
    v_s = max(q_values)

    # Advantage: A(s,a) = Q(s,a) - V(s)
    advantage = q_values[current_action_idx] - v_s

    # Policy entropy
    entropy = round(_entropy(probs), 4)
    exploration_mode = entropy > 1.0

    # Best action under softmax policy
    best_idx = max(range(4), key=lambda i: probs[i])

    action_probs = {ACTIONS[i]: round(probs[i], 4) for i in range(4)}

    return PolicyGradientResult(
        action_probabilities=action_probs,
        advantage=round(advantage, 4),
        temperature=round(temperature, 4),
        policy_entropy=entropy,
        exploration_mode=exploration_mode,
        best_action=ACTIONS[best_idx],
    )


def decay_temperature(temperature: float, decay_rate: float = 0.99, minimum: float = 0.1) -> float:
    """Decay temperature: τ = max(min, τ · decay_rate)."""
    return round(max(minimum, temperature * decay_rate), 4)
