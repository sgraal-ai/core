from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MEWMAResult:
    T2_stat: float
    control_limit: float
    out_of_control: bool
    monitored_components: list[str]
    ewma_vector: dict[str, float]


# Default monitored components
DEFAULT_COMPONENTS = ["s_freshness", "s_drift", "s_provenance", "s_relevance", "r_belief"]


def _mat_vec_mult(mat: list[list[float]], vec: list[float]) -> list[float]:
    """Matrix × vector multiplication."""
    return [sum(mat[i][j] * vec[j] for j in range(len(vec))) for i in range(len(mat))]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(ai * bi for ai, bi in zip(a, b))


def _inverse_diagonal(variances: list[float]) -> list[list[float]]:
    """Inverse of diagonal covariance matrix Σ⁻¹.

    For computational efficiency, we use a diagonal approximation
    (components treated as uncorrelated for Σ). This is the standard
    approach when the full covariance is unknown.
    """
    n = len(variances)
    inv = [[0.0] * n for _ in range(n)]
    for i in range(n):
        inv[i][i] = 1.0 / max(variances[i], 1e-10)
    return inv


def compute_mewma(
    component_breakdown: dict[str, float],
    history: list[dict[str, float]] | None = None,
    lam: float = 0.2,
    control_limit: float = 12.0,
    components: list[str] | None = None,
) -> MEWMAResult:
    """Multivariate EWMA with Hotelling T² control statistic.

    Zₜ = λ·Xₜ + (1-λ)·Zₜ₋₁  (vector EWMA)
    T²ₜ = Zₜᵀ · Σ⁻¹ · Zₜ    (Hotelling T²)

    Alert when T² exceeds control_limit h (default 12, calibrated
    for 5 components at α=0.01).

    Args:
        component_breakdown: current scoring components
        history: optional list of past component breakdowns for EWMA smoothing
        lam: EWMA smoothing parameter (default 0.2)
        control_limit: T² threshold (default 12.0)
        components: which components to monitor (default: 5 key components)

    Returns:
        MEWMAResult with T² statistic, control status, and EWMA vector
    """
    monitored = components or DEFAULT_COMPONENTS
    p = len(monitored)

    # Current observation vector
    x_t = [component_breakdown.get(c, 0.0) for c in monitored]

    # Compute EWMA vector
    if history and len(history) >= 1:
        # Initialize from first observation
        z = [history[0].get(c, 0.0) for c in monitored]

        # Update through history
        for obs in history[1:]:
            x = [obs.get(c, 0.0) for c in monitored]
            z = [lam * x[i] + (1 - lam) * z[i] for i in range(p)]

        # Update with current
        z = [lam * x_t[i] + (1 - lam) * z[i] for i in range(p)]
    else:
        # No history: EWMA = current observation
        z = x_t[:]

    # Estimate baseline (mean) from history or use 50 as neutral
    if history and len(history) >= 2:
        means = [
            sum(obs.get(c, 0.0) for obs in history) / len(history)
            for c in monitored
        ]
        # Variance estimation
        variances = [
            max(1.0, sum((obs.get(c, 0.0) - means[i]) ** 2 for obs in history) / max(len(history) - 1, 1))
            for i, c in enumerate(monitored)
        ]
    else:
        # Default: neutral baseline, unit variance scaled by component range
        means = [25.0] * p  # neutral midpoint for "healthy" scores
        variances = [400.0] * p  # std=20, reasonable for 0-100 range

    # Center the EWMA vector
    z_centered = [z[i] - means[i] for i in range(p)]

    # EWMA variance adjustment: Σ_z = (λ/(2-λ)) · Σ
    ewma_scale = lam / (2.0 - lam)
    adjusted_variances = [v * ewma_scale for v in variances]

    # Hotelling T²: Z'ᵀ · Σ_z⁻¹ · Z'
    sigma_inv = _inverse_diagonal(adjusted_variances)
    temp = _mat_vec_mult(sigma_inv, z_centered)
    T2 = round(_dot(z_centered, temp), 4)
    T2 = max(0.0, T2)  # ensure non-negative

    out_of_control = T2 > control_limit

    ewma_dict = {monitored[i]: round(z[i], 2) for i in range(p)}

    return MEWMAResult(
        T2_stat=T2,
        control_limit=control_limit,
        out_of_control=out_of_control,
        monitored_components=monitored,
        ewma_vector=ewma_dict,
    )
