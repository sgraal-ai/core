from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


COMPONENT_NAMES = [
    "L_IB", "L_RL", "L_EWC", "L_SH", "L_HG",
    "L_FE", "L_OT", "T_XY", "L_LDT", "Var_dN", "L_CA",
]
N_COMPONENTS = 11
DEFAULT_WEIGHT = 1.0 / N_COMPONENTS


@dataclass
class UnifiedLossResult:
    L_v4: float
    components: dict[str, float]
    lambda_weights: list[float]
    dominant_loss: str
    geodesic_update_count: int


def compute_unified_loss(
    L_IB: float = 0.0,       # free_energy ELBO
    L_RL: float = 0.0,       # RL Q-value loss
    L_EWC: float = 0.0,      # consolidation Hopfield energy
    L_SH: float = 0.0,       # zk_sheaf h1_rank
    L_HG: float = 0.0,       # OU current_deviation
    L_FE: float = 0.0,       # free_energy F
    L_OT: float = 0.0,       # sinkhorn wasserstein
    T_XY: float = 0.0,       # transfer_entropy max_flow (NEGATIVE sign)
    L_LDT: float = 0.0,      # levy extreme_event_probability
    Var_dN: float = 0.0,     # jump_diffusion jump_rate_lambda
    L_CA: float = 0.0,       # stability (1 - score)
    lambda_weights: Optional[list[float]] = None,
    geodesic_update_count: int = 0,
) -> UnifiedLossResult:
    """Compute L_v4 Unified Loss — master optimization objective.

    L_v4 = λ₁·L_IB + λ₂·L_RL + λ₃·L_EWC + λ₄·L_SH + λ₅·L_HG
         + λ₆·L_FE + λ₇·L_OT - λ₈·T_{X→Y} + λ₉·L_LDT + λ₁₀·Var(dN) + λ₁₁·L_CA

    Note: T_{X→Y} has NEGATIVE sign (we maximize transfer entropy).

    Args:
        L_IB..L_CA: individual loss components (0.0 fallback for unavailable)
        lambda_weights: 11 weights (default equal 1/11)
        geodesic_update_count: number of geodesic updates applied so far

    Returns:
        UnifiedLossResult
    """
    if lambda_weights is None or len(lambda_weights) != N_COMPONENTS:
        lambda_weights = [DEFAULT_WEIGHT] * N_COMPONENTS

    raw = [L_IB, L_RL, L_EWC, L_SH, L_HG, L_FE, L_OT, T_XY, L_LDT, Var_dN, L_CA]
    signs = [1, 1, 1, 1, 1, 1, 1, -1, 1, 1, 1]  # T_XY negative

    # Compute L_v4
    L_v4 = sum(lambda_weights[i] * signs[i] * raw[i] for i in range(N_COMPONENTS))

    # Components dict
    components = {COMPONENT_NAMES[i]: round(raw[i], 4) for i in range(N_COMPONENTS)}

    # Dominant loss: argmax(|λᵢ · signᵢ · Lᵢ|)
    weighted = [abs(lambda_weights[i] * signs[i] * raw[i]) for i in range(N_COMPONENTS)]
    dom_idx = max(range(N_COMPONENTS), key=lambda i: weighted[i])
    dominant_loss = COMPONENT_NAMES[dom_idx]

    return UnifiedLossResult(
        L_v4=round(L_v4, 4),
        components=components,
        lambda_weights=[round(w, 4) for w in lambda_weights],
        dominant_loss=dominant_loss,
        geodesic_update_count=geodesic_update_count,
    )


def geodesic_update(
    lambda_weights: list[float],
    loss_components: list[float],
    lr: float = 0.01,
    clip_min: float = 0.01,
    clip_max: float = 10.0,
) -> list[float]:
    """Geodesic weight update on λ manifold.

    dλᵢ/dt = -(g(λ)⁻¹)ᵢᵢ · ∂L_v4/∂λᵢ
    Diagonal FIM: g(λ)ᵢᵢ = λᵢ²
    Natural gradient: Δλᵢ = -lr · (1/λᵢ²) · ∂L_v4/∂λᵢ

    ∂L_v4/∂λᵢ = signᵢ · Lᵢ (since L_v4 is linear in λ)

    Args:
        lambda_weights: current weights [11]
        loss_components: current raw loss values [11]
        lr: learning rate (default 0.01)
        clip_min: minimum weight (default 0.01)
        clip_max: maximum weight (default 10.0)

    Returns:
        Updated lambda_weights [11]
    """
    if len(lambda_weights) != N_COMPONENTS or len(loss_components) != N_COMPONENTS:
        return lambda_weights

    signs = [1, 1, 1, 1, 1, 1, 1, -1, 1, 1, 1]
    updated = []

    for i in range(N_COMPONENTS):
        lam = lambda_weights[i]
        grad = signs[i] * loss_components[i]  # ∂L/∂λᵢ

        # Natural gradient: Δλ = -lr · (1/λ²) · grad
        if abs(lam) > 1e-10:
            inv_fim = 1.0 / (lam * lam)
        else:
            inv_fim = 1.0 / (clip_min * clip_min)

        new_lam = lam - lr * inv_fim * grad

        # Clip
        new_lam = max(clip_min, min(clip_max, new_lam))
        updated.append(round(new_lam, 6))

    return updated
