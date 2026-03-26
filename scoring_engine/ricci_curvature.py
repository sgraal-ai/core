from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class EdgeCurvature:
    from_id: str
    to_id: str
    kappa: float


@dataclass
class RicciCurvatureResult:
    edge_curvatures: list[EdgeCurvature]
    mean_curvature: float
    negative_curvature_edges: list[tuple[str, str]]
    graph_health: str  # "healthy" or "fragile"


def _entry_vector(entry: dict) -> list[float]:
    return [
        entry.get("source_trust", 0.5) * 100,
        max(0, 100 - entry.get("timestamp_age_days", 0)),
        (1.0 - (entry.get("source_conflict", 0.1) or 0.1)) * 100,
        max(0, 100 - entry.get("downstream_count", 0) * 10),
    ]


def _euclidean(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(min(len(a), len(b)))))


def _wasserstein_1d_simple(p: list[float], q: list[float]) -> float:
    """Simple 1-Wasserstein between two discrete uniform distributions."""
    if not p or not q:
        return 0.0
    sp = sorted(p)
    sq = sorted(q)
    # Pad shorter to match longer
    n = max(len(sp), len(sq))
    while len(sp) < n:
        sp.append(sp[-1])
    while len(sq) < n:
        sq.append(sq[-1])
    return sum(abs(sp[i] - sq[i]) for i in range(n)) / n


def compute_ricci_curvature(
    entries: list[dict],
    edge_threshold: float = 0.5,
) -> Optional[RicciCurvatureResult]:
    """Ollivier-Ricci curvature on memory entry graph.

    kappa(i,j) = 1 - W1(mu_i, mu_j) / d(i,j)
    W1 = 1-Wasserstein between neighborhood distributions
    d(i,j) = Euclidean distance between component vectors
    mu_i = uniform distribution over neighbors of i

    Positive kappa: stable cluster.
    Negative kappa: fragile bottleneck.

    Args:
        entries: list of dicts with id, source_trust, etc.
        edge_threshold: percentile threshold for edge creation (0-1)

    Returns:
        RicciCurvatureResult or None if < 2 entries
    """
    n = len(entries)
    if n < 2:
        return None

    try:
        vectors = [_entry_vector(e) for e in entries]
        ids = [e.get("id", f"e{i}") for i, e in enumerate(entries)]

        # Pairwise distances
        dist = [[0.0] * n for _ in range(n)]
        all_dists = []
        for i in range(n):
            for j in range(i + 1, n):
                d = _euclidean(vectors[i], vectors[j])
                dist[i][j] = d
                dist[j][i] = d
                all_dists.append(d)

        if not all_dists:
            return None

        # Edge threshold: connect pairs within median distance
        all_dists.sort()
        threshold_dist = all_dists[int(len(all_dists) * edge_threshold)]

        # Build adjacency
        neighbors = [[] for _ in range(n)]
        edges = []
        for i in range(n):
            for j in range(i + 1, n):
                if dist[i][j] <= threshold_dist:
                    neighbors[i].append(j)
                    neighbors[j].append(i)
                    edges.append((i, j))

        # Compute Ollivier-Ricci curvature per edge
        curvatures = []
        neg_edges = []

        for i, j in edges:
            d_ij = dist[i][j]
            if d_ij < 1e-10:
                curvatures.append(EdgeCurvature(from_id=ids[i], to_id=ids[j], kappa=1.0))
                continue

            # Neighborhood distributions: distances from neighbors to the other node
            mu_i_dists = [dist[ni][j] for ni in neighbors[i]] if neighbors[i] else [d_ij]
            mu_j_dists = [dist[nj][i] for nj in neighbors[j]] if neighbors[j] else [d_ij]

            w1 = _wasserstein_1d_simple(mu_i_dists, mu_j_dists)
            kappa = 1.0 - w1 / d_ij
            kappa = round(max(-2.0, min(2.0, kappa)), 4)

            curvatures.append(EdgeCurvature(from_id=ids[i], to_id=ids[j], kappa=kappa))
            if kappa < 0:
                neg_edges.append((ids[i], ids[j]))

        if not curvatures:
            return RicciCurvatureResult(
                edge_curvatures=[],
                mean_curvature=0.0,
                negative_curvature_edges=[],
                graph_health="healthy",
            )

        mean_k = round(sum(c.kappa for c in curvatures) / len(curvatures), 4)
        health = "healthy" if mean_k >= 0 else "fragile"

        return RicciCurvatureResult(
            edge_curvatures=curvatures,
            mean_curvature=mean_k,
            negative_curvature_edges=neg_edges,
            graph_health=health,
        )
    except Exception:
        return None
