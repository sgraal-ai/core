from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class HotellingT2Result:
    t2_statistic: float
    ucl: float
    out_of_control: bool
    components_contributing: list[str]
    phase: str  # "phase1_calibrating" or "phase2_monitoring"


def _chi2_ppf_99(df: int) -> float:
    """Approximate chi-squared inverse CDF at p=0.99.

    Wilson-Hilferty: chi2_p ~ df * (1 - 2/(9df) + z_p*sqrt(2/(9df)))^3
    z_0.99 = 2.3263
    """
    if df <= 0:
        return 0.0
    z = 2.3263
    t = 1.0 - 2.0 / (9 * df) + z * math.sqrt(2.0 / (9 * df))
    return df * t * t * t


def _invert_matrix(M: list[list[float]]) -> Optional[list[list[float]]]:
    """Gauss-Jordan inversion with partial pivoting."""
    d = len(M)
    aug = [[0.0] * (2 * d) for _ in range(d)]
    for i in range(d):
        for j in range(d):
            aug[i][j] = M[i][j]
        aug[i][d + i] = 1.0

    for col in range(d):
        max_row = col
        max_val = abs(aug[col][col])
        for row in range(col + 1, d):
            if abs(aug[row][col]) > max_val:
                max_val = abs(aug[row][col])
                max_row = row
        if max_val < 1e-14:
            return None
        aug[col], aug[max_row] = aug[max_row], aug[col]

        pivot = aug[col][col]
        for j in range(2 * d):
            aug[col][j] /= pivot

        for row in range(d):
            if row != col:
                factor = aug[row][col]
                for j in range(2 * d):
                    aug[row][j] -= factor * aug[col][j]

    return [[aug[i][d + j] for j in range(d)] for i in range(d)]


COMPONENT_KEYS = ["s_freshness", "s_drift", "s_provenance", "s_propagation",
                  "r_recall", "r_encode", "s_interference", "s_recovery",
                  "r_belief", "s_relevance"]


def compute_hotelling_t2(
    component_breakdown: dict[str, float],
    reference_data: Optional[dict] = None,
    regularization: float = 0.01,
) -> Optional[HotellingT2Result]:
    """Hotelling T-squared multivariate control chart.

    T2 = (x-mu)^T * Sigma^-1 * (x-mu)
    UCL = chi2.ppf(0.99, df=n_components)

    Args:
        component_breakdown: current component scores
        reference_data: {"mean": [...], "cov": [[...]], "n_observations": int}
        regularization: Sigma_reg = Sigma + reg*I (default 0.01)

    Returns:
        HotellingT2Result or None on error
    """
    try:
        # Build current vector from components
        keys_present = [k for k in COMPONENT_KEYS if k in component_breakdown]
        if not keys_present:
            return None

        x = [component_breakdown.get(k, 0.0) for k in keys_present]
        d = len(x)

        # Phase determination
        n_obs = reference_data.get("n_observations", 0) if reference_data else 0

        if n_obs < 10 or reference_data is None:
            # Phase 1: calibrating — compute from current data only
            return HotellingT2Result(
                t2_statistic=0.0,
                ucl=round(_chi2_ppf_99(d), 4),
                out_of_control=False,
                components_contributing=[],
                phase="phase1_calibrating",
            )

        # Phase 2: monitoring with reference
        mu = reference_data.get("mean", [0.0] * d)
        cov = reference_data.get("cov")

        if mu is None or len(mu) != d:
            mu = [0.0] * d

        if cov is None or len(cov) != d:
            # Build diagonal covariance from reference
            cov = [[regularization if i == j else 0.0 for j in range(d)] for i in range(d)]
        else:
            # Add regularization
            for i in range(d):
                cov[i][i] += regularization

        # Invert covariance
        inv_cov = _invert_matrix(cov)
        if inv_cov is None:
            return None

        # T2 = (x-mu)^T * Sigma^-1 * (x-mu)
        diff = [x[i] - mu[i] for i in range(d)]
        temp = [sum(inv_cov[j][k] * diff[k] for k in range(d)) for j in range(d)]
        t2 = sum(diff[j] * temp[j] for j in range(d))
        t2 = max(0.0, t2)

        ucl = _chi2_ppf_99(d)
        ooc = t2 > ucl

        # Find contributing components: those with |diff| > 1 std
        contributing = []
        if ooc:
            for i, k in enumerate(keys_present):
                std_i = math.sqrt(max(cov[i][i], 1e-10))
                if abs(diff[i]) > std_i:
                    contributing.append(k)

        return HotellingT2Result(
            t2_statistic=round(t2, 4),
            ucl=round(ucl, 4),
            out_of_control=ooc,
            components_contributing=contributing,
            phase="phase2_monitoring",
        )
    except Exception:
        return None
