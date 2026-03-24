from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class CalibrationResult:
    brier_score: float
    log_loss: float
    calibrated_scores: dict[str, float]
    meta_score: float


def _brier_score(assurance: float, omega: float) -> float:
    """Brier score: BS = (forecast - outcome)².

    forecast = assurance_score / 100 (probability of safe outcome)
    outcome = 1 if omega < 25 (USE_MEMORY), else 0

    Lower is better. Perfect = 0, worst = 1.
    """
    f = assurance / 100.0
    o = 1.0 if omega < 25 else 0.0
    return round((f - o) ** 2, 4)


def _log_loss(assurance: float, omega: float) -> float:
    """Log loss: L(y,p) = -(y·log(p) + (1-y)·log(1-p)).

    Penalizes confident wrong decisions heavily.
    """
    eps = 1e-10
    p = max(eps, min(1 - eps, assurance / 100.0))
    y = 1.0 if omega < 25 else 0.0
    return round(-(y * math.log(p) + (1 - y) * math.log(1 - p)), 4)


def _softmax_temperature(scores: dict[str, float], T: float = 1.5) -> dict[str, float]:
    """Softmax temperature scaling: pᵢ = exp(zᵢ/T) / Σⱼ exp(zⱼ/T).

    T > 1 smooths overconfident scores (more uniform).
    T < 1 sharpens (more peaked).
    T = 1 standard softmax.
    """
    if not scores:
        return {}

    vals = list(scores.values())
    max_val = max(vals) if vals else 0
    # Numerically stable softmax
    exps = {k: math.exp((v - max_val) / T) for k, v in scores.items()}
    total = sum(exps.values()) or 1.0
    return {k: round((v / total) * 100, 2) for k, v in exps.items()}


def _logistic_meta(components: dict[str, float]) -> float:
    """Logistic meta-layer: P(unsafe) = σ(β₀ + Σ βᵢ·Cᵢ).

    Pre-trained coefficients (from domain analysis):
    - Intercept biases toward safe (negative β₀)
    - Freshness, drift, interference weighted higher
    - Recovery reduces risk (negative coefficient)
    """
    # Meta-layer coefficients (learned from scoring patterns)
    betas = {
        "_intercept": -3.0,
        "s_freshness": 0.04,
        "s_drift": 0.035,
        "s_provenance": 0.02,
        "s_propagation": 0.015,
        "r_recall": 0.025,
        "r_encode": 0.01,
        "s_interference": 0.03,
        "s_recovery": -0.02,
        "r_belief": 0.02,
        "s_relevance": 0.015,
    }

    z = betas["_intercept"]
    for k, beta in betas.items():
        if k == "_intercept":
            continue
        z += beta * components.get(k, 0)

    # Sigmoid
    p = 1.0 / (1.0 + math.exp(-z))
    return round(p * 100, 2)  # scale to 0–100


def compute_calibration(
    omega_mem_final: float,
    assurance_score: float,
    component_breakdown: dict[str, float],
    temperature: float = 1.5,
) -> CalibrationResult:
    """Compute all calibration metrics.

    Args:
        omega_mem_final: the raw Ω_MEM score
        assurance_score: the assurance score (0–100)
        component_breakdown: dict of component scores
        temperature: softmax temperature (default 1.5)

    Returns:
        CalibrationResult with brier_score, log_loss, calibrated_scores, meta_score
    """
    return CalibrationResult(
        brier_score=_brier_score(assurance_score, omega_mem_final),
        log_loss=_log_loss(assurance_score, omega_mem_final),
        calibrated_scores=_softmax_temperature(component_breakdown, temperature),
        meta_score=_logistic_meta(component_breakdown),
    )
