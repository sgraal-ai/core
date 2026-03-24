from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CausalEdge:
    from_id: str
    to_id: str
    strength: float
    confirmed: bool = False  # True when cross-validated with transfer entropy


@dataclass
class CausalGraphResult:
    edges: list[CausalEdge]
    root_cause: Optional[str]
    causal_chain: list[str]
    causal_explanation: str


def _standardize(values: list[float]) -> list[float]:
    """Zero mean, unit variance standardization."""
    n = len(values)
    if n < 2:
        return [0.0] * n
    mu = sum(values) / n
    var = sum((x - mu) ** 2 for x in values) / (n - 1)
    std = math.sqrt(var) if var > 0 else 1.0
    return [(x - mu) / std for x in values]


def _correlation(a: list[float], b: list[float]) -> float:
    """Pearson correlation coefficient."""
    n = len(a)
    if n < 2:
        return 0.0
    ma = sum(a) / n
    mb = sum(b) / n
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / (n - 1)
    sa = math.sqrt(sum((x - ma) ** 2 for x in a) / (n - 1)) if n > 1 else 1.0
    sb = math.sqrt(sum((x - mb) ** 2 for x in b) / (n - 1)) if n > 1 else 1.0
    if sa == 0 or sb == 0:
        return 0.0
    return cov / (sa * sb)


def _residual(y: list[float], x: list[float]) -> list[float]:
    """OLS residual: y - β·x where β = cov(x,y)/var(x)."""
    n = len(y)
    if n < 2:
        return y[:]
    mx = sum(x) / n
    my = sum(y) / n
    var_x = sum((xi - mx) ** 2 for xi in x) / (n - 1)
    if var_x == 0:
        return y[:]
    cov_xy = sum((x[i] - mx) * (y[i] - my) for i in range(n)) / (n - 1)
    beta = cov_xy / var_x
    return [y[i] - beta * x[i] for i in range(n)]


def _kurtosis(values: list[float]) -> float:
    """Excess kurtosis (non-Gaussian measure). Higher abs = more non-Gaussian."""
    n = len(values)
    if n < 4:
        return 0.0
    mu = sum(values) / n
    m2 = sum((x - mu) ** 2 for x in values) / n
    m4 = sum((x - mu) ** 4 for x in values) / n
    if m2 == 0:
        return 0.0
    return (m4 / (m2 ** 2)) - 3.0


def compute_causal_graph(
    entries: list[dict],
    histories: Optional[dict[str, list[float]]] = None,
    prune_threshold: float = 0.1,
    min_observations: int = 10,
) -> Optional[CausalGraphResult]:
    """Simplified DirectLiNGAM causal discovery between memory entries.

    Algorithm:
    1. Standardize entry score histories
    2. Find causal ordering via non-Gaussianity (kurtosis-based ICA approx)
    3. OLS regression for edge weights
    4. Prune edges below threshold

    Args:
        entries: list of dicts with id, content, and optional score history
        histories: dict mapping entry_id → list of historical scores (≥10 obs)
        prune_threshold: minimum edge strength to keep (default 0.1)
        min_observations: minimum history length per entry (default 10)

    Returns:
        CausalGraphResult or None if insufficient data
    """
    n = len(entries)
    if n < 2:
        return None

    ids = [e["id"] for e in entries]

    # Build score matrix from histories or entry metadata
    if histories:
        # Filter entries with sufficient history
        valid_ids = [eid for eid in ids if eid in histories and len(histories[eid]) >= min_observations]
        if len(valid_ids) < 2:
            return None
        ids = valid_ids
        n = len(ids)
        scores = {eid: _standardize(histories[eid]) for eid in ids}
    else:
        # Fallback: use entry metadata as single-observation proxy
        # Build synthetic scores from available fields
        score_data = {}
        for e in entries:
            score_data[e["id"]] = [
                e.get("timestamp_age_days", 0),
                e.get("source_trust", 0.9) * 100,
                e.get("source_conflict", 0.1) * 100,
                e.get("downstream_count", 1) * 10,
            ]
        # Need at least min_observations — with metadata we have 4 features
        # Use cross-entry correlation instead
        if n < 2:
            return None

        # Build pairwise regression from metadata
        edges: list[CausalEdge] = []
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                ei, ej = entries[i], entries[j]
                # Causal strength heuristic: older entry with more downstream → likely cause
                age_i = ei.get("timestamp_age_days", 0)
                age_j = ej.get("timestamp_age_days", 0)
                dc_i = ei.get("downstream_count", 1)
                dc_j = ej.get("downstream_count", 1)

                # Older entry with higher downstream likely causes newer
                if age_i > age_j and dc_i >= dc_j:
                    strength = round(min(1.0, (age_i - age_j) / max(age_i, 1) * dc_i / 10), 4)
                    if strength >= prune_threshold:
                        edges.append(CausalEdge(from_id=ids[i], to_id=ids[j], strength=strength))

        return _build_result(edges, ids)

    # DirectLiNGAM approximation with kurtosis-based ordering
    # Step 1: Find causal ordering by non-Gaussianity after residualization
    obs_len = min(len(scores[eid]) for eid in ids)
    remaining = list(range(n))
    order: list[int] = []

    current_data = {i: scores[ids[i]][:obs_len] for i in range(n)}

    for _ in range(n):
        # Find the most exogenous variable (highest abs kurtosis of residuals)
        best_idx = remaining[0]
        best_kurt = -1.0

        for idx in remaining:
            kurt = abs(_kurtosis(current_data[idx]))
            if kurt > best_kurt:
                best_kurt = kurt
                best_idx = idx

        order.append(best_idx)
        remaining.remove(best_idx)

        # Residualize remaining variables against the chosen one
        for idx in remaining:
            current_data[idx] = _residual(current_data[idx], current_data[best_idx])

    # Step 2: OLS regression for edge weights following causal order
    edges: list[CausalEdge] = []
    for pos in range(1, len(order)):
        effect_idx = order[pos]
        effect_data = scores[ids[effect_idx]][:obs_len]

        for cause_pos in range(pos):
            cause_idx = order[cause_pos]
            cause_data = scores[ids[cause_idx]][:obs_len]

            # OLS: β = cov(cause, effect) / var(cause)
            corr = _correlation(cause_data, effect_data)
            strength = round(abs(corr), 4)

            if strength >= prune_threshold:
                edges.append(CausalEdge(
                    from_id=ids[cause_idx],
                    to_id=ids[effect_idx],
                    strength=strength,
                ))

    return _build_result(edges, ids)


def _build_result(edges: list[CausalEdge], ids: list[str]) -> CausalGraphResult:
    """Build CausalGraphResult from edges."""
    if not edges:
        return CausalGraphResult(
            edges=[],
            root_cause=None,
            causal_chain=[],
            causal_explanation="No significant causal relationships detected.",
        )

    # Root cause: node with most outgoing edges (or strongest)
    out_strength: dict[str, float] = {}
    for e in edges:
        out_strength[e.from_id] = out_strength.get(e.from_id, 0) + e.strength

    root_cause = max(out_strength, key=out_strength.get) if out_strength else None

    # Causal chain: BFS from root cause
    chain = []
    if root_cause:
        chain = [root_cause]
        visited = {root_cause}
        queue = [root_cause]
        while queue:
            node = queue.pop(0)
            for e in edges:
                if e.from_id == node and e.to_id not in visited:
                    chain.append(e.to_id)
                    visited.add(e.to_id)
                    queue.append(e.to_id)

    # Explanation
    if root_cause and len(edges) > 0:
        affected = [e.to_id for e in edges if e.from_id == root_cause]
        affected_str = " and ".join(affected[:3])
        explanation = (
            f"{root_cause} drifted and causally affects {affected_str} "
            f"— this is the true risk source."
        )
    else:
        explanation = "No significant causal relationships detected."

    return CausalGraphResult(
        edges=edges,
        root_cause=root_cause,
        causal_chain=chain,
        causal_explanation=explanation,
    )
