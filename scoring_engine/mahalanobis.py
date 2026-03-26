from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


COMPONENT_KEYS = ["s_freshness", "s_drift", "s_provenance", "s_relevance", "r_belief"]


@dataclass
class EntryDistance:
    entry_id: str
    distance: float
    is_anomaly: bool


@dataclass
class MahalanobisResult:
    distances: list[EntryDistance]
    mean_distance: float
    anomaly_count: int
    covariance_condition: float
    chi2_threshold: float


def _chi2_ppf_95(df: int) -> float:
    """Approximate chi-squared inverse CDF at p=0.95 for given df.

    Uses Wilson-Hilferty approximation:
    χ²_p ≈ df · (1 - 2/(9·df) + z_p · sqrt(2/(9·df)))³
    where z_0.95 = 1.6449.
    """
    if df <= 0:
        return 0.0
    z = 1.6449
    t = 1.0 - 2.0 / (9 * df) + z * math.sqrt(2.0 / (9 * df))
    return df * t * t * t


def _entry_to_vector(entry: dict) -> list[float]:
    """Extract component vector from entry metadata."""
    trust = entry.get("source_trust", 0.5)
    age = entry.get("timestamp_age_days", 0)
    conflict = entry.get("source_conflict", 0.1)
    downstream = entry.get("downstream_count", 0)
    r_belief = entry.get("r_belief", 0.0)

    # Map to component-like scores (0-100 scale)
    s_freshness = min(100, age * 1.5)  # older = higher freshness risk
    s_drift = conflict * 100  # higher conflict = higher drift proxy
    s_provenance = (1.0 - trust) * 100  # lower trust = higher provenance risk
    s_relevance = min(100, downstream * 5)  # more downstream = more relevance risk
    r_belief_score = r_belief * 100 if r_belief else 0.0

    return [s_freshness, s_drift, s_provenance, s_relevance, r_belief_score]


def compute_mahalanobis(
    entries: list[dict],
    regularization: float = 0.01,
) -> Optional[MahalanobisResult]:
    """Mahalanobis distance for multivariate state anomaly detection.

    D_M(x,μ) = sqrt((x-μ)ᵀ · Σ⁻¹ · (x-μ))

    Anomaly when D_M > chi2.ppf(0.95, df=n_components).

    Args:
        entries: list of dicts with source_trust, timestamp_age_days, etc.
        regularization: Σ_reg = Σ + reg·I (default 0.01)

    Returns:
        MahalanobisResult or None if n_entries < 3
    """
    n = len(entries)
    if n < 3:
        return None

    try:
        # Build component vectors
        vectors = [_entry_to_vector(e) for e in entries]
        d = len(vectors[0])  # dimensionality

        # Mean vector
        mu = [sum(vectors[i][j] for i in range(n)) / n for j in range(d)]

        # Covariance matrix Σ with regularization
        # Σ_jk = (1/n) Σᵢ (x_ij - μ_j)(x_ik - μ_k) + reg·δ_jk
        cov = [[0.0] * d for _ in range(d)]
        for j in range(d):
            for k in range(d):
                s = sum((vectors[i][j] - mu[j]) * (vectors[i][k] - mu[k]) for i in range(n)) / n
                cov[j][k] = s + (regularization if j == k else 0.0)

        # Invert covariance via Gauss-Jordan elimination
        # Build augmented matrix [Σ | I]
        aug = [[0.0] * (2 * d) for _ in range(d)]
        for i in range(d):
            for j in range(d):
                aug[i][j] = cov[i][j]
            aug[i][d + i] = 1.0

        # Forward elimination with partial pivoting
        for col in range(d):
            # Find pivot
            max_row = col
            max_val = abs(aug[col][col])
            for row in range(col + 1, d):
                if abs(aug[row][col]) > max_val:
                    max_val = abs(aug[row][col])
                    max_row = row
            if max_val < 1e-12:
                return None  # singular even with regularization
            aug[col], aug[max_row] = aug[max_row], aug[col]

            pivot = aug[col][col]
            for j in range(2 * d):
                aug[col][j] /= pivot

            for row in range(d):
                if row != col:
                    factor = aug[row][col]
                    for j in range(2 * d):
                        aug[row][j] -= factor * aug[col][j]

        # Extract inverse
        inv_cov = [[aug[i][d + j] for j in range(d)] for i in range(d)]

        # Covariance condition number: max_diag / min_diag
        diag = [cov[i][i] for i in range(d)]
        cov_condition = max(diag) / max(min(diag), 1e-10)

        # Chi-squared threshold at 95% with df = n_components
        threshold = _chi2_ppf_95(d)

        # Compute Mahalanobis distance for each entry
        distances = []
        anomaly_count = 0

        for idx, e in enumerate(entries):
            x = vectors[idx]
            diff = [x[j] - mu[j] for j in range(d)]

            # (x-μ)ᵀ · Σ⁻¹ · (x-μ)
            temp = [sum(inv_cov[j][k] * diff[k] for k in range(d)) for j in range(d)]
            d_sq = sum(diff[j] * temp[j] for j in range(d))
            d_m = math.sqrt(max(0.0, d_sq))

            is_anomaly = d_m > threshold
            if is_anomaly:
                anomaly_count += 1

            distances.append(EntryDistance(
                entry_id=e.get("id", f"entry_{idx}"),
                distance=round(d_m, 4),
                is_anomaly=is_anomaly,
            ))

        mean_dist = round(sum(ed.distance for ed in distances) / max(n, 1), 4)

        return MahalanobisResult(
            distances=distances,
            mean_distance=mean_dist,
            anomaly_count=anomaly_count,
            covariance_condition=round(cov_condition, 4),
            chi2_threshold=round(threshold, 4),
        )
    except Exception:
        return None
