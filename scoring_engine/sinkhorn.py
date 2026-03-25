from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class SinkhornResult:
    distance: float          # Sinkhorn-regularized OT distance
    iterations: int          # number of iterations to converge
    converged: bool          # whether algorithm converged


def _l2_cost_matrix(p_vals: list[float], q_vals: list[float]) -> list[list[float]]:
    """Build L2 cost matrix C_ij = (p_i - q_j)²."""
    n = len(p_vals)
    m = len(q_vals)
    C = [[0.0] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            C[i][j] = (p_vals[i] - q_vals[j]) ** 2
    return C


def sinkhorn_distance(
    p: list[float],
    q: list[float],
    p_vals: Optional[list[float]] = None,
    q_vals: Optional[list[float]] = None,
    epsilon: float = 0.1,
    max_iter: int = 100,
    threshold: float = 1e-6,
) -> Optional[SinkhornResult]:
    """Sinkhorn optimal transport distance.

    W_ε(P,Q) = min_{γ∈Π} Σᵢⱼ γᵢⱼ Cᵢⱼ + ε·KL(γ‖P⊗Q)

    Iterative: u ← a/(Kv), v ← b/(Kᵀu), K = exp(-C/ε)

    Args:
        p: source distribution (probability weights, sums to 1)
        q: target distribution (probability weights, sums to 1)
        p_vals: source support values (defaults to indices 0..n-1)
        q_vals: target support values (defaults to indices 0..m-1)
        epsilon: entropic regularization parameter (default 0.1)
        max_iter: maximum Sinkhorn iterations (default 100)
        threshold: convergence threshold (default 1e-6)

    Returns:
        SinkhornResult or None on error
    """
    n = len(p)
    m = len(q)

    if n == 0 or m == 0:
        return None

    try:
        # Default support: indices
        if p_vals is None:
            p_vals = [float(i) for i in range(n)]
        if q_vals is None:
            q_vals = [float(j) for j in range(m)]

        # Build cost matrix
        C = _l2_cost_matrix(p_vals, q_vals)

        # Normalize cost matrix: C = C / C.max() + 1e-8
        c_max = max(C[i][j] for i in range(n) for j in range(m))
        if c_max > 1e-10:
            for i in range(n):
                for j in range(m):
                    C[i][j] = C[i][j] / c_max + 1e-8
        else:
            # All costs are zero — distributions at same points
            return SinkhornResult(distance=0.0, iterations=0, converged=True)

        # Gibbs kernel K = exp(-C/ε)
        K = [[0.0] * m for _ in range(n)]
        for i in range(n):
            for j in range(m):
                K[i][j] = math.exp(-C[i][j] / epsilon)

        # Ensure p, q are proper distributions
        eps = 1e-10
        p_sum = sum(p) or 1.0
        q_sum = sum(q) or 1.0
        a = [max(pi / p_sum, eps) for pi in p]
        b = [max(qi / q_sum, eps) for qi in q]

        # Initialize u, v
        u = [1.0] * n
        v = [1.0] * m

        converged = False
        iterations = 0

        for it in range(max_iter):
            iterations = it + 1

            # v ← b / (Kᵀu)
            v_new = [0.0] * m
            for j in range(m):
                kt_u_j = sum(K[i][j] * u[i] for i in range(n))
                v_new[j] = b[j] / max(kt_u_j, eps)
            v = v_new

            # u ← a / (Kv)
            u_new = [0.0] * n
            for i in range(n):
                kv_i = sum(K[i][j] * v[j] for j in range(m))
                u_new[i] = a[i] / max(kv_i, eps)

            # Check convergence: max |u_new - u| / max(|u|, 1)
            max_diff = max(abs(u_new[i] - u[i]) for i in range(n))
            max_u = max(abs(x) for x in u) or 1.0
            u = u_new

            if max_diff / max_u < threshold:
                converged = True
                break

        # Compute transport distance: W = Σᵢⱼ uᵢ Kᵢⱼ vⱼ Cᵢⱼ
        distance = 0.0
        for i in range(n):
            for j in range(m):
                gamma_ij = u[i] * K[i][j] * v[j]
                distance += gamma_ij * C[i][j]

        # Rescale by c_max to get original-scale distance
        distance *= c_max

        return SinkhornResult(
            distance=round(distance, 4),
            iterations=iterations,
            converged=converged,
        )
    except Exception:
        return None
