from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class FrechetResult:
    fd_score: float
    mean_shift: float
    covariance_shift: float
    encoding_degraded: bool
    reference_age_steps: int


def _mean_vector(vectors: list[list[float]]) -> list[float]:
    """Compute mean vector across samples."""
    n = len(vectors)
    d = len(vectors[0])
    return [sum(vectors[i][j] for i in range(n)) / n for j in range(d)]


def _covariance_matrix(vectors: list[list[float]], mu: list[float], reg: float = 1e-6) -> list[list[float]]:
    """Compute covariance matrix with regularization: Σ + reg·I."""
    n = len(vectors)
    d = len(mu)
    cov = [[0.0] * d for _ in range(d)]
    for j in range(d):
        for k in range(d):
            cov[j][k] = sum((vectors[i][j] - mu[j]) * (vectors[i][k] - mu[k]) for i in range(n)) / max(n - 1, 1)
            if j == k:
                cov[j][k] += reg
    return cov


def _mat_mul(A: list[list[float]], B: list[list[float]]) -> list[list[float]]:
    """Matrix multiplication A·B."""
    n = len(A)
    m = len(B[0])
    k = len(B)
    C = [[0.0] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            C[i][j] = sum(A[i][p] * B[p][j] for p in range(k))
    return C


def _mat_trace(A: list[list[float]]) -> float:
    """Trace of square matrix."""
    return sum(A[i][i] for i in range(len(A)))


def _mat_sqrtm(A: list[list[float]], max_iter: int = 50, tol: float = 1e-8) -> list[list[float]]:
    """Matrix square root via Denman-Beavers iteration.

    Y_{k+1} = ½(Y_k + Z_k⁻¹)
    Z_{k+1} = ½(Z_k + Y_k⁻¹)
    Converges: Y → A^{1/2}, Z → A^{-1/2}

    Falls back to diagonal approximation if iteration fails.
    """
    d = len(A)

    # Start: Y₀ = A, Z₀ = I
    Y = [row[:] for row in A]
    Z = [[1.0 if i == j else 0.0 for j in range(d)] for i in range(d)]

    for _ in range(max_iter):
        # Invert Z and Y
        Z_inv = _invert(Z)
        Y_inv = _invert(Y)
        if Z_inv is None or Y_inv is None:
            break

        # Y_{k+1} = ½(Y + Z⁻¹), Z_{k+1} = ½(Z + Y⁻¹)
        Y_new = [[0.5 * (Y[i][j] + Z_inv[i][j]) for j in range(d)] for i in range(d)]
        Z_new = [[0.5 * (Z[i][j] + Y_inv[i][j]) for j in range(d)] for i in range(d)]

        # Check convergence
        diff = max(abs(Y_new[i][j] - Y[i][j]) for i in range(d) for j in range(d))
        Y = Y_new
        Z = Z_new
        if diff < tol:
            return Y

    # Fallback: diagonal square root
    return [[math.sqrt(max(A[i][j], 0.0)) if i == j else 0.0 for j in range(d)] for i in range(d)]


def _invert(M: list[list[float]]) -> Optional[list[list[float]]]:
    """Gauss-Jordan matrix inversion."""
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


def compute_frechet(
    current_vectors: list[list[float]],
    reference_vectors: Optional[list[list[float]]] = None,
    reference_age_steps: int = 0,
    degradation_threshold: float = 10.0,
) -> Optional[FrechetResult]:
    """Fréchet distance for embedding quality degradation detection.

    FD = ||μ_P - μ_Q||² + Tr(Σ_P + Σ_Q - 2·sqrt(Σ_P·Σ_Q))

    Uses component score vectors as embedding proxy.

    Args:
        current_vectors: current entry component vectors
        reference_vectors: stored reference distribution (None = first call)
        reference_age_steps: how many steps since reference was set
        degradation_threshold: fd_score above this = encoding_degraded (default 10.0)

    Returns:
        FrechetResult or None if < 3 entries or no reference
    """
    if len(current_vectors) < 3:
        return None

    if reference_vectors is None or len(reference_vectors) < 3:
        # No reference available — return neutral result (A2 axiom: deterministic)
        return FrechetResult(
            fd_score=0.0,
            mean_shift=0.0,
            covariance_shift=0.0,
            encoding_degraded=False,
            reference_age_steps=0,
        )

    try:
        d = len(current_vectors[0])
        d_ref = len(reference_vectors[0])
        if d != d_ref or d == 0:
            return None

        # Current distribution stats
        mu_p = _mean_vector(current_vectors)
        sigma_p = _covariance_matrix(current_vectors, mu_p)

        # Reference distribution stats
        mu_q = _mean_vector(reference_vectors)
        sigma_q = _covariance_matrix(reference_vectors, mu_q)

        # Mean shift: ||μ_P - μ_Q||²
        mean_shift = sum((mu_p[i] - mu_q[i]) ** 2 for i in range(d))

        # Covariance shift: Tr(Σ_P + Σ_Q - 2·sqrt(Σ_P·Σ_Q))
        product = _mat_mul(sigma_p, sigma_q)
        sqrt_product = _mat_sqrtm(product)

        trace_p = _mat_trace(sigma_p)
        trace_q = _mat_trace(sigma_q)
        trace_sqrt = _mat_trace(sqrt_product)

        cov_shift = trace_p + trace_q - 2 * trace_sqrt
        cov_shift = max(0.0, cov_shift)  # numerical stability

        fd = mean_shift + cov_shift
        encoding_degraded = fd > degradation_threshold

        return FrechetResult(
            fd_score=round(fd, 4),
            mean_shift=round(mean_shift, 4),
            covariance_shift=round(cov_shift, 4),
            encoding_degraded=encoding_degraded,
            reference_age_steps=reference_age_steps,
        )
    except Exception:
        return None
