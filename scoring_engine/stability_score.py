from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class StabilityResult:
    score: float                    # 0.0 (unstable) → 1.0 (perfectly stable)
    components: dict[str, float]    # per-component raw values
    interpretation: str             # "stable", "degrading", "critical"
    component_count: int = 9        # 9 or 10 (with lyapunov)


def compute_r_total(
    alpha_divergence_score: float = 0.0,
    s_drift: float = 0.0,
    s_interference: float = 0.0,
    omega_mem_final: float = 0.0,
    fiedler_value: float = 0.0,
) -> float:
    """R_total normalized (DeepSeek formula — scale-independent monitoring).

    R_total = Δα/Δα₀ + β/β₀ + H/H₀ + ω₀/ω₀_crit + λ₂/λ₂_crit

    Normalization constants:
        Δα₀ = 2.0, β₀ = 1.0, H₀ = 1.0, ω₀_crit = 100.0, λ₂_crit = 5.0

    Returns:
        R_total capped at 5.0
    """
    da0, b0, h0, w0_crit, l2_crit = 2.0, 1.0, 1.0, 100.0, 5.0

    r = (
        alpha_divergence_score / da0
        + s_drift / b0
        + s_interference / h0
        + omega_mem_final / w0_crit
        + fiedler_value / l2_crit
    )

    return round(min(r, 5.0), 4)


# Per-axis polytope temperatures (from research/results/ten_findings_batch1.json §15.3)
# Normalized to sum=1: PC1=0.574 (Trust), PC2=0.239 (Decay), PC3=0.132 (Trust-residual),
# PC4=0.055 (Drift), PC5=0.000 (Belief-frozen).
#
# Each stability component is mapped to its dominant polytope axis so weighting by
# axis temperature transfers to the multi-component stability formula. Components
# not clearly on one axis get the average weight.
_AXIS_WEIGHTS = {
    # Trust-axis (PC1) — dominant
    "delta_alpha": 0.574,        # provenance trust drift
    "p_transition": 0.574,       # HMM Trust state transitions
    # Decay-axis (PC2)
    "omega_drift": 0.239,        # freshness drift
    "omega_0": 0.239,            # baseline omega
    # Trust-residual (PC3)
    "lambda_2": 0.132,           # graph connectivity
    "hurst": 0.132,              # temporal persistence
    # Drift-axis (PC4)
    "h1_rank": 0.055,            # sheaf inconsistency
    "tau_mix": 0.055,            # mixing time
    # Belief-axis (PC5, frozen) — use small epsilon to avoid zero total
    "d_geo_causal": 0.001,
    "lyapunov_lambda": 0.001,
    "colimit_state": 0.001,
}


def compute_stability_score(
    delta_alpha: float = 0.0,
    p_transition: float = 0.0,
    omega_drift: float = 0.0,
    omega_0: float = 0.0,
    lambda_2: float = 0.0,
    hurst: float = 0.0,
    h1_rank: float = 0.0,
    tau_mix: float = 0.0,
    d_geo_causal: float = 0.0,
    lyapunov_lambda: Optional[float] = None,
    colimit_state: Optional[float] = None,
    use_temperature_weights: bool = False,
) -> StabilityResult:
    """StabilityScore 9 or 10-component formula.

    Default (equal weights): StabilityScore = (1/N) · Σₖ (1 - Componentₖ/Componentₖ_max)

    With use_temperature_weights=True: weight each component by its polytope axis
    temperature (PC1=0.574, PC2=0.239, PC3=0.132, PC4=0.055, PC5≈0). Research
    (§15.3) showed axis temperatures span 10.4× — equal weighting over-weights
    the frozen Belief axis and under-weights the dominant Trust axis.

    9 components (base):
        delta_alpha: 2.0, p_transition: 1.0, omega_drift: 1.0,
        omega_0: 1.0, lambda_2: 5.0, hurst: 1.0,
        h1_rank: 10.0, tau_mix: 100.0, d_geo_causal: 2.0

    10th component (when lyapunov available):
        lyapunov_lambda: 1.0 (max, using max(0, λ))

    Returns:
        StabilityResult with score (0-1), components, interpretation, component_count
    """
    maxes = {
        "delta_alpha": 2.0,
        "p_transition": 1.0,
        "omega_drift": 1.0,
        "omega_0": 1.0,
        "lambda_2": 5.0,
        "hurst": 1.0,
        "h1_rank": 10.0,
        "tau_mix": 100.0,
        "d_geo_causal": 2.0,
    }

    raw = {
        "delta_alpha": delta_alpha,
        "p_transition": p_transition,
        "omega_drift": omega_drift,
        "omega_0": omega_0,
        "lambda_2": lambda_2,
        "hurst": hurst,
        "h1_rank": h1_rank,
        "tau_mix": tau_mix,
        "d_geo_causal": d_geo_causal,
    }

    n_components = 9

    # Add 10th component if lyapunov available
    if lyapunov_lambda is not None:
        raw["lyapunov_lambda"] = max(0.0, lyapunov_lambda)
        maxes["lyapunov_lambda"] = 1.0
        n_components = 10

    # Add 11th component if colimit available
    if colimit_state is not None:
        # Higher global_state = more risk (inverted: 1 - global_state already handled by formula)
        raw["colimit_state"] = max(0.0, min(1.0, colimit_state))
        maxes["colimit_state"] = 1.0
        n_components += 1

    if use_temperature_weights:
        # Weighted sum — each component's (1 - cap/max) contribution is scaled by axis temperature
        total_weight = sum(_AXIS_WEIGHTS.get(k, 0.0) for k in raw.keys())
        if total_weight <= 0:
            total_weight = 1.0
        total = 0.0
        for key, val in raw.items():
            capped = min(val, maxes[key])
            w = _AXIS_WEIGHTS.get(key, 0.0) / total_weight
            total += w * (1.0 - capped / maxes[key])
        score = round(total, 4)
    else:
        total = 0.0
        for key, val in raw.items():
            capped = min(val, maxes[key])
            total += 1.0 - capped / maxes[key]
        score = round(total / n_components, 4)
    score = max(0.0, min(1.0, score))

    if score > 0.7:
        interpretation = "stable"
    elif score >= 0.4:
        interpretation = "degrading"
    else:
        interpretation = "critical"

    return StabilityResult(
        score=score,
        components=raw,
        interpretation=interpretation,
        component_count=n_components,
    )
