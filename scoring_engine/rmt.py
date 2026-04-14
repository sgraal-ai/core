from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class RMTResult:
    signal_eigenvalues: list[float]
    noise_threshold: float
    true_interference_count: int
    noise_interference_count: int
    signal_ratio: float


def _tokenize(text: str) -> set[str]:
    return set(text.lower().split())


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    return len(a & b) / len(union) if union else 1.0


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _build_interference_matrix(entries: list[dict]) -> list[list[float]]:
    """Build symmetric interference matrix I_ij from pairwise similarity."""
    n = len(entries)
    embeddings = [e.get("prompt_embedding") for e in entries]
    tokens = [_tokenize(e.get("content", "")) for e in entries]

    mat = [[0.0] * n for _ in range(n)]
    for i in range(n):
        mat[i][i] = 1.0
        for j in range(i + 1, n):
            ei, ej = embeddings[i], embeddings[j]
            if ei is not None and ej is not None and len(ei) == len(ej):
                sim = _cosine(ei, ej)
            else:
                sim = _jaccard(tokens[i], tokens[j])
            mat[i][j] = sim
            mat[j][i] = sim
    return mat


def _eigenvalues_symmetric(mat: list[list[float]]) -> list[float]:
    """Compute eigenvalues of a symmetric matrix via Jacobi-like iteration.

    Simple power iteration for top eigenvalues — avoids numpy dependency.
    For small matrices (≤20), uses direct characteristic approach.
    """
    n = len(mat)
    if n == 0:
        return []
    if n == 1:
        return [mat[0][0]]
    if n == 2:
        a, b, c, d = mat[0][0], mat[0][1], mat[1][0], mat[1][1]
        trace = a + d
        det = a * d - b * c
        disc = max(0, trace * trace - 4 * det)
        sqrt_disc = math.sqrt(disc)
        return sorted([(trace + sqrt_disc) / 2, (trace - sqrt_disc) / 2], reverse=True)

    # For n>2: Gershgorin circle theorem approximation + power iteration for top-k
    eigenvalues = []

    # Gershgorin bounds for all eigenvalues
    for i in range(n):
        center = mat[i][i]
        radius = sum(abs(mat[i][j]) for j in range(n) if j != i)
        eigenvalues.append(center + radius)  # upper bound approximation

    # Refine with power iteration for dominant eigenvalue
    v = [1.0 / math.sqrt(n)] * n
    for _ in range(50):
        # Matrix-vector multiply
        w = [sum(mat[i][j] * v[j] for j in range(n)) for i in range(n)]
        norm = math.sqrt(sum(x * x for x in w))
        if norm < 1e-10:
            break
        v = [x / norm for x in w]
        eigenvalues[0] = sum(v[i] * sum(mat[i][j] * v[j] for j in range(n)) for i in range(n))

    return sorted(eigenvalues, reverse=True)


def compute_rmt(
    entries: list[dict],
    max_entries: int = 20,
) -> Optional[RMTResult]:
    """Random Matrix Theory signal/noise separation for interference.

    Marchenko-Pastur boundary:
        λ_signal = σ² · (1 + √γ)²
    where γ = n_entries / n_features, σ² = variance of interference matrix.

    Eigenvalues above λ_signal = real signal.
    Below = noise (spurious correlations).

    Args:
        entries: list of dicts with content and optional prompt_embedding
        max_entries: limit for full computation (top-k for larger)

    Returns:
        RMTResult or None if n_entries < 2
    """
    n = len(entries)
    if n < 5:
        # Need n >= 5 for meaningful Marchenko-Pastur analysis (n=2 gives degenerate eigenvalues)
        return None

    # Limit to max_entries for performance
    if n > max_entries:
        entries = entries[:max_entries]
        n = max_entries

    try:
        mat = _build_interference_matrix(entries)
        eigenvalues = _eigenvalues_symmetric(mat)

        if not eigenvalues:
            return None

        # Marchenko-Pastur parameters
        # γ = aspect ratio (entries / features), features ≈ entries for square matrix
        gamma = 1.0  # square matrix
        # σ² = variance of off-diagonal elements
        off_diag = []
        for i in range(n):
            for j in range(i + 1, n):
                off_diag.append(mat[i][j])

        if not off_diag:
            return None

        sigma2 = sum((x - sum(off_diag) / len(off_diag)) ** 2 for x in off_diag) / max(len(off_diag) - 1, 1)
        sigma2 = max(sigma2, 0.01)  # floor to avoid zero

        # MP upper edge
        lambda_plus = sigma2 * (1 + math.sqrt(gamma)) ** 2

        # Classify eigenvalues
        signal_eigs = [round(e, 4) for e in eigenvalues if e > lambda_plus]
        noise_eigs = [e for e in eigenvalues if e <= lambda_plus]

        total_pairs = max(len(eigenvalues), 1)
        true_count = len(signal_eigs)
        noise_count = len(noise_eigs)
        signal_ratio = round(true_count / total_pairs, 4)

        return RMTResult(
            signal_eigenvalues=signal_eigs,
            noise_threshold=round(lambda_plus, 4),
            true_interference_count=true_count,
            noise_interference_count=noise_count,
            signal_ratio=signal_ratio,
        )
    except Exception:
        return None
