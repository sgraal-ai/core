from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class StabilityResult:
    score: float                    # 0.0 (unstable) → 1.0 (perfectly stable)
    components: dict[str, float]    # per-component raw values
    interpretation: str             # "stable", "degrading", "critical"


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
) -> StabilityResult:
    """StabilityScore 9-component formula (Grok formula).

    StabilityScore = (1/9) · Σₖ (1 - Componentₖ/Componentₖ_max)

    Components and max values:
        delta_alpha: 2.0, p_transition: 1.0, omega_drift: 1.0,
        omega_0: 1.0, lambda_2: 5.0, hurst: 1.0,
        h1_rank: 10.0, tau_mix: 100.0, d_geo_causal: 2.0

    Returns:
        StabilityResult with score (0-1), components, and interpretation
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

    total = 0.0
    for key, val in raw.items():
        capped = min(val, maxes[key])
        total += 1.0 - capped / maxes[key]

    score = round(total / 9.0, 4)
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
    )
