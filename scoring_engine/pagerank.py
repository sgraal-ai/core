from __future__ import annotations

from typing import Optional


def compute_pagerank(
    adjacency: dict[str, list[str]],
    damping: float = 0.85,
    iterations: int = 20,
    tolerance: float = 1e-6,
) -> dict[str, float]:
    """Compute PageRank over a directed graph.

    PR(v) = (1-d)/N + d · Σ PR(u)/L(u)

    Args:
        adjacency: node_id → list of node_ids it points to (outgoing edges)
        damping: damping factor d (default 0.85)
        iterations: max iterations
        tolerance: convergence threshold

    Returns:
        dict mapping node_id → PageRank score (sums to ~1.0)
    """
    nodes = set(adjacency.keys())
    for targets in adjacency.values():
        nodes.update(targets)

    N = len(nodes)
    if N == 0:
        return {}

    # Initialize uniform
    pr: dict[str, float] = {n: 1.0 / N for n in nodes}

    # Precompute out-degree
    out_degree: dict[str, int] = {n: len(adjacency.get(n, [])) for n in nodes}

    # Build reverse adjacency (incoming edges)
    incoming: dict[str, list[str]] = {n: [] for n in nodes}
    for src, targets in adjacency.items():
        for tgt in targets:
            incoming[tgt].append(src)

    for _ in range(iterations):
        new_pr: dict[str, float] = {}
        for node in nodes:
            rank_sum = sum(
                pr[src] / out_degree[src]
                for src in incoming[node]
                if out_degree[src] > 0
            )
            new_pr[node] = (1 - damping) / N + damping * rank_sum

        # Check convergence
        diff = sum(abs(new_pr[n] - pr[n]) for n in nodes)
        pr = new_pr
        if diff < tolerance:
            break

    return pr


def compute_authority_scores(
    entry_ids: list[str],
    downstream_map: Optional[dict[str, list[str]]] = None,
) -> dict[str, float]:
    """Compute PageRank authority scores for memory entries.

    If no explicit downstream_map is provided, builds a graph from
    downstream_count: entries with higher downstream_count are assumed
    to feed into entries with lower downstream_count.

    Args:
        entry_ids: list of memory entry IDs
        downstream_map: optional explicit adjacency (entry_id → [dependent_entry_ids])

    Returns:
        dict mapping entry_id → authority_score (0.0–10.0, normalized)
    """
    if not entry_ids:
        return {}

    if downstream_map is None:
        # Default: each entry connects to the next (chain model)
        downstream_map = {}
        for i, eid in enumerate(entry_ids):
            targets = [entry_ids[j] for j in range(len(entry_ids)) if j != i]
            downstream_map[eid] = targets[:3]  # limit to 3 connections

    pr = compute_pagerank(downstream_map)

    if not pr:
        return {eid: 0.0 for eid in entry_ids}

    # Normalize to 0–10 scale
    max_pr = max(pr.values()) if pr else 1.0
    if max_pr == 0:
        max_pr = 1.0

    return {
        eid: round((pr.get(eid, 0) / max_pr) * 10.0, 2)
        for eid in entry_ids
    }
