from __future__ import annotations

from typing import Optional

from .omega_mem import WEIGHTS, C_ACTION, C_DOMAIN


def compute_shapley_values(
    component_breakdown: dict[str, float],
    action_type: str = "reversible",
    domain: str = "general",
    custom_weights: Optional[dict[str, float]] = None,
) -> dict[str, float]:
    """Compute Shapley values for each component's contribution to Ω_MEM.

    Uses marginal contribution: for each component, compute the score
    with vs without it. For our linear weighted model, Shapley values
    equal weight × component_value × multiplier, normalized so they
    sum to the final omega_mem_final.

    Returns dict mapping component name → contribution to final score.
    Positive = increases risk, negative = decreases risk (e.g. s_recovery).
    """
    weights = custom_weights if custom_weights else WEIGHTS
    c = C_ACTION.get(action_type, 1.0) * C_DOMAIN.get(domain, 1.0)

    # Raw weighted contributions
    raw: dict[str, float] = {}
    for k, v in component_breakdown.items():
        w = weights.get(k, WEIGHTS.get(k, 0))
        raw[k] = w * v

    # The raw omega before clamping and multiplier
    raw_omega = sum(raw.values())
    raw_omega_clamped = max(0, min(100, raw_omega))

    # Apply multiplier to get final contributions
    # If raw_omega is within [0, 100], each contribution scales by c
    # If clamped, we proportionally attribute the clamped total
    omega_final = min(100, raw_omega_clamped * c)

    if raw_omega == 0:
        return {k: 0.0 for k in component_breakdown}

    # Scale factor: how much of each raw contribution survives after clamping + multiplier
    scale = omega_final / raw_omega if raw_omega != 0 else 0

    shapley: dict[str, float] = {}
    for k in component_breakdown:
        shapley[k] = round(raw[k] * scale, 2)

    return shapley
