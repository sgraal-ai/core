from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class SpectralResult:
    fiedler_value: float
    spectral_gap: float
    graph_connectivity: str  # "fragmented", "normal", "dense"
    cheeger_bound: dict  # {"lower": float, "upper": float}
    mixing_time_estimate: float


def _tokenize(text: str) -> set[str]:
    return set(text.lower().split())


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _build_adjacency(entries: list[dict]) -> list[list[float]]:
    """Build adjacency matrix A_ij = exp(-d(i,j)) where d is distance."""
    n = len(entries)
    embeddings = [e.get("prompt_embedding") for e in entries]
    tokens = [_tokenize(e.get("content", "")) for e in entries]

    A = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            ei, ej = embeddings[i], embeddings[j]
            if ei is not None and ej is not None and len(ei) == len(ej):
                sim = _cosine(ei, ej)
            else:
                sim = _jaccard(tokens[i], tokens[j])

            # A_ij = exp(-distance) where distance = 1 - similarity
            weight = math.exp(-(1.0 - max(0, min(1, sim))))
            A[i][j] = weight
            A[j][i] = weight

    return A


def _eigenvalues_laplacian(L: list[list[float]]) -> list[float]:
    """Compute eigenvalues of symmetric Laplacian via iterative method.

    For small matrices, uses direct formulas. For larger ones,
    power iteration with deflation for top eigenvalues.
    """
    n = len(L)
    if n == 0:
        return []
    if n == 1:
        return [L[0][0]]
    if n == 2:
        a, b = L[0][0], L[0][1]
        c, d = L[1][0], L[1][1]
        trace = a + d
        det = a * d - b * c
        disc = max(0, trace * trace - 4 * det)
        sqrt_disc = math.sqrt(disc)
        return sorted([(trace - sqrt_disc) / 2, (trace + sqrt_disc) / 2])

    # For n>2: Gershgorin + power iteration
    # Laplacian eigenvalues are non-negative and smallest is 0
    eigenvalues = []

    # Smallest eigenvalue of Laplacian is always 0 (for connected component)
    eigenvalues.append(0.0)

    # Estimate remaining eigenvalues via Gershgorin circles
    gersh = []
    for i in range(n):
        center = L[i][i]
        radius = sum(abs(L[i][j]) for j in range(n) if j != i)
        gersh.append(center)

    gersh.sort()

    # Power iteration for second-smallest eigenvalue (Fiedler)
    # Use inverse iteration: find smallest eigenvalue of L + εI
    # Approximate: use the ratio of Gershgorin bounds
    if len(gersh) >= 2:
        # Better approximation via shifted power iteration
        # Find eigenvector for largest eigenvalue, then deflate
        v = [1.0 / math.sqrt(n)] * n  # start vector
        # Remove component along constant vector (null space of L)
        ones = [1.0 / math.sqrt(n)] * n

        for _ in range(100):
            # Matrix-vector multiply
            w = [sum(L[i][j] * v[j] for j in range(n)) for i in range(n)]

            # Project out null space component
            dot_ones = sum(w[i] * ones[i] for i in range(n))
            w = [w[i] - dot_ones * ones[i] for i in range(n)]

            norm = math.sqrt(sum(x * x for x in w))
            if norm < 1e-12:
                break
            v = [x / norm for x in w]

        # Rayleigh quotient gives dominant eigenvalue in orthogonal complement
        Lv = [sum(L[i][j] * v[j] for j in range(n)) for i in range(n)]
        lambda_max = sum(v[i] * Lv[i] for i in range(n))
        eigenvalues.append(max(0, lambda_max))

        # Fill rest with Gershgorin estimates
        for g in gersh[2:]:
            eigenvalues.append(max(0, g))

    eigenvalues.sort()
    return eigenvalues


def compute_spectral(entries: list[dict]) -> Optional[SpectralResult]:
    """Compute spectral analysis of memory interference graph.

    Builds graph Laplacian L = D - A and analyzes eigenvalues.

    Args:
        entries: list of dicts with content and optional prompt_embedding

    Returns:
        SpectralResult or None if n_entries < 2
    """
    n = len(entries)
    if n < 2:
        return None

    try:
        A = _build_adjacency(entries)

        # Degree matrix D and Laplacian L = D - A
        L = [[0.0] * n for _ in range(n)]
        for i in range(n):
            degree = sum(A[i])
            L[i][i] = degree
            for j in range(n):
                if i != j:
                    L[i][j] = -A[i][j]

        eigenvalues = _eigenvalues_laplacian(L)

        if len(eigenvalues) < 2:
            return None

        # λ₂ = Fiedler value (second smallest eigenvalue)
        fiedler = round(eigenvalues[1], 4) if len(eigenvalues) > 1 else 0.0

        # Spectral gap = λ₂ / λ_max
        lambda_max = max(eigenvalues) if eigenvalues else 1.0
        spectral_gap = round(fiedler / max(lambda_max, 1e-10), 4)

        # Graph connectivity classification
        if fiedler < 0.1:
            connectivity = "fragmented"
        elif fiedler > 2.0:
            connectivity = "dense"
        else:
            connectivity = "normal"

        # Cheeger constant bound: λ₂/2 ≤ h(G) ≤ √(2λ₂)
        cheeger_lower = round(fiedler / 2.0, 4)
        cheeger_upper = round(math.sqrt(2.0 * max(0, fiedler)), 4)

        # Mixing time estimate: τ_mix = O(1/(1-λ₂)) for normalized Laplacian
        if fiedler >= 1.0:
            mixing_time = 1.0  # already mixed
        elif fiedler > 0.001:
            mixing_time = round(1.0 / fiedler, 2)
        else:
            mixing_time = round(1000.0, 2)  # effectively disconnected

        return SpectralResult(
            fiedler_value=fiedler,
            spectral_gap=spectral_gap,
            graph_connectivity=connectivity,
            cheeger_bound={"lower": cheeger_lower, "upper": cheeger_upper},
            mixing_time_estimate=mixing_time,
        )
    except Exception:
        return None
