from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


FILTRATION_SCALES = [0.1, 0.5, 1.0, 2.0, 5.0]


@dataclass
class BettiAtScale:
    scale: float
    count: int


@dataclass
class PersistentHomologyResult:
    betti_0: list[BettiAtScale]
    betti_1: list[BettiAtScale]
    significant_features: int
    structural_drift: bool
    topology_summary: str  # "simple", "looped", "complex"


def _entry_vector(entry: dict) -> list[float]:
    """Build component vector from entry metadata."""
    return [
        entry.get("source_trust", 0.5) * 100,
        max(0, 100 - entry.get("timestamp_age_days", 0)),
        (1.0 - (entry.get("source_conflict", 0.1) or 0.1)) * 100,
        max(0, 100 - entry.get("downstream_count", 0) * 10),
    ]


def _euclidean(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(min(len(a), len(b)))))


def _connected_components(adj: list[list[bool]], n: int) -> int:
    """Count connected components via BFS."""
    visited = [False] * n
    components = 0
    for start in range(n):
        if visited[start]:
            continue
        components += 1
        queue = [start]
        visited[start] = True
        while queue:
            node = queue.pop(0)
            for j in range(n):
                if adj[node][j] and not visited[j]:
                    visited[j] = True
                    queue.append(j)
    return components


def _count_edges(adj: list[list[bool]], n: int) -> int:
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            if adj[i][j]:
                count += 1
    return count


def compute_persistent_homology(
    entries: list[dict],
) -> Optional[PersistentHomologyResult]:
    """Simplified persistent homology via Vietoris-Rips filtration.

    beta_0: connected components (BFS)
    beta_1: edges - nodes + components (Euler characteristic)
    Filtration at scales [0.1, 0.5, 1.0, 2.0, 5.0].

    Args:
        entries: list of dicts with source_trust, timestamp_age_days, etc.

    Returns:
        PersistentHomologyResult or None if < 3 entries
    """
    n = len(entries)
    if n < 3:
        return None

    try:
        vectors = [_entry_vector(e) for e in entries]

        # Pairwise distance matrix
        dist = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                d = _euclidean(vectors[i], vectors[j])
                dist[i][j] = d
                dist[j][i] = d

        # Normalize distances to [0, ~5] range
        max_dist = max(dist[i][j] for i in range(n) for j in range(n) if i != j) or 1.0

        betti_0_list = []
        betti_1_list = []
        max_b1 = 0

        for eps in FILTRATION_SCALES:
            threshold = eps * max_dist / 5.0  # scale relative to data

            adj = [[False] * n for _ in range(n)]
            for i in range(n):
                for j in range(i + 1, n):
                    if dist[i][j] < threshold:
                        adj[i][j] = True
                        adj[j][i] = True

            comp = _connected_components(adj, n)
            edges = _count_edges(adj, n)

            # beta_1 = edges - nodes + components (from Euler: V - E + F = chi)
            b1 = max(0, edges - n + comp)

            betti_0_list.append(BettiAtScale(scale=eps, count=comp))
            betti_1_list.append(BettiAtScale(scale=eps, count=b1))
            max_b1 = max(max_b1, b1)

        # Significant features: persistence > 0.5
        # Count features that appear at one scale and disappear at another
        sig = 0
        for i in range(len(FILTRATION_SCALES) - 1):
            if betti_0_list[i].count != betti_0_list[i + 1].count:
                sig += 1
            if betti_1_list[i].count != betti_1_list[i + 1].count:
                sig += 1

        structural_drift = max_b1 > 0

        if max_b1 == 0:
            topology = "simple"
        elif max_b1 <= 2:
            topology = "looped"
        else:
            topology = "complex"

        return PersistentHomologyResult(
            betti_0=betti_0_list,
            betti_1=betti_1_list,
            significant_features=sig,
            structural_drift=structural_drift,
            topology_summary=topology,
        )
    except Exception:
        return None
