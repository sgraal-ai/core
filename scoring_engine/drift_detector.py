from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class DriftMetrics:
    kl_divergence: float
    wasserstein: float
    jsd: float
    drift_method: str = "ensemble"
    ensemble_score: float = 0.0


def _kl_divergence(p: list[float], q: list[float]) -> float:
    """KL(P||Q) = Σ p_i · log(p_i / q_i). Smoothed to avoid log(0)."""
    eps = 1e-10
    return sum(
        pi * math.log((pi + eps) / (qi + eps))
        for pi, qi in zip(p, q)
    )


def _wasserstein_1d(p: list[float], q: list[float]) -> float:
    """1D Wasserstein (Earth Mover's) distance between two distributions."""
    # CDF-based: W = Σ |CDF_p(i) - CDF_q(i)|
    cum_p, cum_q = 0.0, 0.0
    dist = 0.0
    for pi, qi in zip(p, q):
        cum_p += pi
        cum_q += qi
        dist += abs(cum_p - cum_q)
    return dist


def _jsd(p: list[float], q: list[float]) -> float:
    """Jensen-Shannon divergence: JSD(P,Q) = ½·KL(P||M) + ½·KL(Q||M) where M=(P+Q)/2."""
    m = [(pi + qi) / 2.0 for pi, qi in zip(p, q)]
    return 0.5 * _kl_divergence(p, m) + 0.5 * _kl_divergence(q, m)


def compute_drift_metrics(
    current_scores: list[float],
    baseline_scores: list[float] | None = None,
    weights: tuple[float, float, float] = (1/3, 1/3, 1/3),
) -> DriftMetrics:
    """Compute ensemble drift metrics from current and baseline score distributions.

    If no baseline provided, uses a uniform "healthy" distribution as reference.

    Args:
        current_scores: list of component scores (0–100) from current scoring
        baseline_scores: optional reference distribution (same length)
        weights: (w_kl, w_wasserstein, w_jsd) for ensemble, default equal

    Returns:
        DriftMetrics with all three metrics + ensemble score (0–100)
    """
    if not current_scores:
        return DriftMetrics(0, 0, 0, ensemble_score=0)

    n = len(current_scores)

    # Normalize to probability distributions
    total_c = sum(current_scores) or 1.0
    p = [s / total_c for s in current_scores]

    if baseline_scores and len(baseline_scores) == n:
        total_b = sum(baseline_scores) or 1.0
        q = [s / total_b for s in baseline_scores]
    else:
        # Uniform baseline (all components equally weighted = no drift)
        q = [1.0 / n] * n

    kl = _kl_divergence(p, q)
    wass = _wasserstein_1d(p, q)
    jsd_val = _jsd(p, q)

    # Scale to 0–100 for consistency with other components
    # KL can be unbounded, cap at reasonable values
    kl_scaled = min(100, kl * 100)
    wass_scaled = min(100, wass * 100)
    # JSD is bounded [0, ln(2)] ≈ 0.693, scale to 0–100
    jsd_scaled = min(100, (jsd_val / 0.693) * 100)

    w_kl, w_wass, w_jsd = weights
    ensemble = w_kl * kl_scaled + w_wass * wass_scaled + w_jsd * jsd_scaled
    ensemble = round(min(100, max(0, ensemble)), 1)

    return DriftMetrics(
        kl_divergence=round(kl_scaled, 2),
        wasserstein=round(wass_scaled, 2),
        jsd=round(jsd_scaled, 2),
        drift_method="ensemble",
        ensemble_score=ensemble,
    )
