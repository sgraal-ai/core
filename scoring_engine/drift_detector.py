from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AlphaDivergence:
    alpha_0_5: float  # Hellinger distance
    alpha_1_5: float
    alpha_2_0: float


@dataclass
class MMDResult:
    score: float
    sigma: float
    kernel: str = "rbf"


@dataclass
class DriftMetrics:
    kl_divergence: float
    wasserstein: float
    jsd: float
    drift_method: str = "ensemble"
    ensemble_score: float = 0.0
    alpha_divergence: Optional[AlphaDivergence] = None
    sinkhorn_used: bool = False
    sinkhorn_iterations: int = 0
    mmd: Optional[MMDResult] = None


def _kl_divergence(p: list[float], q: list[float]) -> float:
    """KL(P||Q) = Σ p_i · log(p_i / q_i). Smoothed to avoid log(0)."""
    eps = 1e-10
    return sum(
        pi * math.log((pi + eps) / (qi + eps))
        for pi, qi in zip(p, q)
    )


def _wasserstein_1d(p: list[float], q: list[float]) -> float:
    """1D Wasserstein (Earth Mover's) distance between two distributions."""
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


def _alpha_divergence(p: list[float], q: list[float], alpha: float) -> float:
    """α-Divergence: D_α(P||Q) = 1/(α(1-α)) · (1 - ∫ p^α · q^(1-α) dx).

    Special cases: α→1 ≈ KL, α=0.5 ≈ Hellinger distance.
    Uses log-space computation for numerical stability.
    """
    eps = 1e-8
    if abs(alpha) < eps or abs(1 - alpha) < eps:
        # Degenerate cases — fall back to KL
        return _kl_divergence(p, q)

    # Compute ∫ p^α · q^(1-α) dx in log-space
    integral = 0.0
    for pi, qi in zip(p, q):
        pi_s = pi + eps
        qi_s = qi + eps
        # p^α · q^(1-α) = exp(α·log(p) + (1-α)·log(q))
        log_term = alpha * math.log(pi_s) + (1 - alpha) * math.log(qi_s)
        integral += math.exp(log_term)

    divergence = (1.0 - integral) / (alpha * (1.0 - alpha))
    return max(0.0, divergence)


def compute_alpha_divergences(p: list[float], q: list[float]) -> Optional[AlphaDivergence]:
    """Compute α-divergence for α ∈ {0.5, 1.5, 2.0}."""
    try:
        a05 = _alpha_divergence(p, q, 0.5)
        a15 = _alpha_divergence(p, q, 1.5)
        a20 = _alpha_divergence(p, q, 2.0)

        # Scale to 0–100 for consistency
        # α=0.5 (Hellinger): bounded [0, 2], scale ×50
        a05_scaled = min(100, a05 * 50)
        # α=1.5 and α=2.0: can be larger, cap
        a15_scaled = min(100, a15 * 100)
        a20_scaled = min(100, a20 * 100)

        return AlphaDivergence(
            alpha_0_5=round(a05_scaled, 2),
            alpha_1_5=round(a15_scaled, 2),
            alpha_2_0=round(a20_scaled, 2),
        )
    except Exception:
        return None


def _rbf_kernel(x: float, y: float, sigma: float) -> float:
    """RBF kernel: k(x,y) = exp(-|x-y|² / (2σ²))."""
    if sigma < 1e-10:
        return 1.0 if abs(x - y) < 1e-10 else 0.0
    return math.exp(-(x - y) ** 2 / (2 * sigma * sigma))


def compute_mmd(p_samples: list[float], q_samples: list[float]) -> Optional[MMDResult]:
    """Maximum Mean Discrepancy with RBF kernel.

    MMD²(P,Q) = E[k(X,X')] + E[k(Y,Y')] - 2E[k(X,Y)]
    σ = median heuristic: σ = median(||xᵢ-xⱼ||) / sqrt(2)

    Args:
        p_samples: samples from distribution P
        q_samples: samples from distribution Q

    Returns:
        MMDResult or None if < 2 samples per distribution
    """
    n = len(p_samples)
    m = len(q_samples)
    if n < 2 or m < 2:
        return None

    try:
        # Check if all samples identical
        all_vals = p_samples + q_samples
        if max(all_vals) - min(all_vals) < 1e-10:
            return MMDResult(score=0.0, sigma=0.0)

        # Median heuristic for σ
        dists = []
        for i in range(len(all_vals)):
            for j in range(i + 1, len(all_vals)):
                dists.append(abs(all_vals[i] - all_vals[j]))
        dists.sort()
        median_dist = dists[len(dists) // 2] if dists else 1.0
        sigma = median_dist / math.sqrt(2) if median_dist > 0 else 1.0

        # E[k(X,X')] — kernel expectation within P
        kxx = 0.0
        count_xx = 0
        for i in range(n):
            for j in range(i + 1, n):
                kxx += _rbf_kernel(p_samples[i], p_samples[j], sigma)
                count_xx += 1
        kxx = kxx / max(count_xx, 1)

        # E[k(Y,Y')] — kernel expectation within Q
        kyy = 0.0
        count_yy = 0
        for i in range(m):
            for j in range(i + 1, m):
                kyy += _rbf_kernel(q_samples[i], q_samples[j], sigma)
                count_yy += 1
        kyy = kyy / max(count_yy, 1)

        # E[k(X,Y)] — cross-kernel expectation
        kxy = 0.0
        for i in range(n):
            for j in range(m):
                kxy += _rbf_kernel(p_samples[i], q_samples[j], sigma)
        kxy = kxy / (n * m)

        mmd_sq = kxx + kyy - 2 * kxy
        mmd_val = math.sqrt(max(0.0, mmd_sq))

        return MMDResult(
            score=round(mmd_val, 4),
            sigma=round(sigma, 4),
        )
    except Exception:
        return None


def compute_drift_metrics(
    current_scores: list[float],
    baseline_scores: list[float] | None = None,
    weights: tuple[float, float, float] = (1/3, 1/3, 1/3),
) -> DriftMetrics:
    """Compute ensemble drift metrics from current and baseline score distributions.

    If no baseline provided, uses a uniform "healthy" distribution as reference.
    Includes α-divergence as 4th method when computable.

    Args:
        current_scores: list of component scores (0–100) from current scoring
        baseline_scores: optional reference distribution (same length)
        weights: (w_kl, w_wasserstein, w_jsd) for 3-method ensemble, default equal

    Returns:
        DriftMetrics with all metrics + ensemble score (0–100)
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
        q = [1.0 / n] * n

    kl = _kl_divergence(p, q)
    jsd_val = _jsd(p, q)

    # Wasserstein: Sinkhorn for n > 5, exact for n ≤ 5
    sinkhorn_used = False
    sinkhorn_iterations = 0
    if n > 5:
        from .sinkhorn import sinkhorn_distance
        sk = sinkhorn_distance(p, q)
        if sk is not None and sk.converged:
            wass = sk.distance
            sinkhorn_used = True
            sinkhorn_iterations = sk.iterations
        else:
            # Fallback to exact Wasserstein
            wass = _wasserstein_1d(p, q)
    else:
        wass = _wasserstein_1d(p, q)

    # Scale to 0–100
    kl_scaled = min(100, kl * 100)
    wass_scaled = min(100, wass * 100)
    jsd_scaled = min(100, (jsd_val / 0.693) * 100)

    # α-Divergence (4th method)
    alpha_div = compute_alpha_divergences(p, q)

    # MMD (5th method) — requires >= 2 samples per distribution
    mmd_result = None
    if n >= 2:
        try:
            mmd_result = compute_mmd(p, q)
        except Exception:
            pass

    if alpha_div is not None and mmd_result is not None:
        # 5-method ensemble (equal weights: 0.2 each)
        alpha_avg = (alpha_div.alpha_0_5 + alpha_div.alpha_1_5 + alpha_div.alpha_2_0) / 3.0
        mmd_scaled = min(100, mmd_result.score * 100)
        ensemble = 0.2 * kl_scaled + 0.2 * wass_scaled + 0.2 * jsd_scaled + 0.2 * alpha_avg + 0.2 * mmd_scaled
        drift_method = "ensemble_5"
    elif alpha_div is not None:
        # 4-method ensemble (equal weights: 0.25 each)
        alpha_avg = (alpha_div.alpha_0_5 + alpha_div.alpha_1_5 + alpha_div.alpha_2_0) / 3.0
        ensemble = 0.25 * kl_scaled + 0.25 * wass_scaled + 0.25 * jsd_scaled + 0.25 * alpha_avg
        drift_method = "ensemble_4"
    else:
        # Fallback: 3-method ensemble
        w_kl, w_wass, w_jsd = weights
        ensemble = w_kl * kl_scaled + w_wass * wass_scaled + w_jsd * jsd_scaled
        drift_method = "ensemble_3"

    ensemble = round(min(100, max(0, ensemble)), 1)

    return DriftMetrics(
        kl_divergence=round(kl_scaled, 2),
        wasserstein=round(wass_scaled, 2),
        jsd=round(jsd_scaled, 2),
        drift_method=drift_method,
        ensemble_score=ensemble,
        alpha_divergence=alpha_div,
        sinkhorn_used=sinkhorn_used,
        sinkhorn_iterations=sinkhorn_iterations,
        mmd=mmd_result,
    )
