from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Default Weibull parameters
DEFAULT_K = 1.5
DEFAULT_LAMBDA = 10.0


@dataclass
class MTTRResult:
    mttr_estimate: float
    mttr_p95: float
    recovery_probability: float
    weibull_k: float
    weibull_lambda: float
    sla_compliant: bool
    data_points: int


def _gamma_function(z: float) -> float:
    """Lanczos approximation of Γ(z) for z > 0.

    Γ(z) ≈ sqrt(2π/z) · (z + g + 0.5)^(z+0.5) · e^-(z+g+0.5) · Σ cᵢ/(z+i)
    """
    if z < 0.5:
        # Reflection formula: Γ(z)·Γ(1-z) = π/sin(πz)
        return math.pi / (math.sin(math.pi * z) * _gamma_function(1 - z))

    z -= 1
    g = 7
    coefficients = [
        0.99999999999980993,
        676.5203681218851,
        -1259.1392167224028,
        771.32342877765313,
        -176.61502916214059,
        12.507343278686905,
        -0.13857109526572012,
        9.9843695780195716e-6,
        1.5056327351493116e-7,
    ]

    x = coefficients[0]
    for i in range(1, g + 2):
        x += coefficients[i] / (z + i)

    t = z + g + 0.5
    return math.sqrt(2 * math.pi) * t ** (z + 0.5) * math.exp(-t) * x


def _estimate_weibull(durations: list[float]) -> tuple[float, float]:
    """Estimate Weibull k (shape) and λ (scale) from duration data.

    Uses method of moments:
    E[X] = λ·Γ(1+1/k)
    E[X²] = λ²·Γ(1+2/k)
    Var(X) = λ²·[Γ(1+2/k) - Γ(1+1/k)²]

    Iterative estimation of k from CV = std/mean.
    """
    n = len(durations)
    if n < 2:
        return DEFAULT_K, DEFAULT_LAMBDA

    pos_durations = [d for d in durations if d > 0]
    if len(pos_durations) < 2:
        return DEFAULT_K, DEFAULT_LAMBDA

    mean_d = sum(pos_durations) / len(pos_durations)
    var_d = sum((d - mean_d) ** 2 for d in pos_durations) / len(pos_durations)

    if mean_d < 1e-10:
        return DEFAULT_K, DEFAULT_LAMBDA

    cv = math.sqrt(var_d) / mean_d if mean_d > 0 else 1.0

    # Approximate k from CV using bisection
    # CV² = Γ(1+2/k)/Γ(1+1/k)² - 1
    k = DEFAULT_K
    for trial_k in [x * 0.1 for x in range(1, 100)]:
        if trial_k < 0.1:
            continue
        try:
            g1 = _gamma_function(1 + 1 / trial_k)
            g2 = _gamma_function(1 + 2 / trial_k)
            if g1 > 0:
                cv_est = math.sqrt(g2 / (g1 * g1) - 1) if g2 / (g1 * g1) > 1 else 0
                if abs(cv_est - cv) < abs(_gamma_function(1 + 1 / k) - cv):
                    k = trial_k
        except (ValueError, OverflowError):
            continue

    # λ from mean = λ·Γ(1+1/k)
    g1 = _gamma_function(1 + 1 / k)
    lam = mean_d / g1 if g1 > 0 else DEFAULT_LAMBDA

    return k, lam


def compute_mttr(
    heal_durations: Optional[list[float]] = None,
    sla_threshold: float = 20.0,
) -> Optional[MTTRResult]:
    """Compute Mean Time to Recovery via Weibull estimation.

    MTTR = λ · Γ(1 + 1/k)
    p95 = λ · (-log(0.05))^(1/k)
    P(recovery < 10) = 1 - exp(-(10/λ)^k)

    Args:
        heal_durations: list of past heal duration values (steps)
        sla_threshold: p95 threshold for SLA compliance (default 20)

    Returns:
        MTTRResult or None on error
    """
    try:
        data_points = len(heal_durations) if heal_durations else 0

        if heal_durations and data_points >= 5:
            k, lam = _estimate_weibull(heal_durations)
        else:
            k, lam = DEFAULT_K, DEFAULT_LAMBDA

        # Validate parameters
        if k <= 0 or lam <= 0:
            logger.warning("invalid Weibull parameters k=%.3f lambda=%.3f, using defaults", k, lam)
            k, lam = DEFAULT_K, DEFAULT_LAMBDA

        # MTTR = λ · Γ(1 + 1/k)
        g1 = _gamma_function(1 + 1 / k)
        mttr = lam * g1

        # p95 = λ · (-log(0.05))^(1/k)
        mttr_p95 = lam * ((-math.log(0.05)) ** (1 / k))

        # Recovery probability within 10 steps: P(T < 10) = 1 - exp(-(10/λ)^k)
        recovery_prob = 1.0 - math.exp(-((10.0 / lam) ** k))

        sla_compliant = mttr_p95 < sla_threshold

        return MTTRResult(
            mttr_estimate=round(mttr, 2),
            mttr_p95=round(mttr_p95, 2),
            recovery_probability=round(recovery_prob, 4),
            weibull_k=round(k, 4),
            weibull_lambda=round(lam, 4),
            sla_compliant=sla_compliant,
            data_points=data_points,
        )
    except Exception:
        return None
