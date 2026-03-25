from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class EntryConsolidation:
    entry_id: str
    consolidation_score: float
    stable: bool


@dataclass
class ConsolidationResult:
    scores: list[EntryConsolidation]
    mean_consolidation: float
    fragile_entries: list[str]
    replay_priority: list[str]


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def _shannon_entropy(values: list[float]) -> float:
    """H(X) = -Σ p_i · log(p_i)."""
    total = sum(values) or 1.0
    probs = [v / total for v in values if v > 0]
    if not probs:
        return 0.0
    return -sum(p * math.log(p + 1e-10) for p in probs)


def _mutual_information(old_dist: list[float], new_dist: list[float]) -> float:
    """Simplified MI: correlation-based proxy.

    MI(X,Y) ≈ -0.5 · log(1 - ρ²) where ρ is Pearson correlation.
    """
    n = min(len(old_dist), len(new_dist))
    if n < 2:
        return 0.0

    mo = sum(old_dist[:n]) / n
    mn = sum(new_dist[:n]) / n

    var_o = sum((x - mo) ** 2 for x in old_dist[:n]) / n
    var_n = sum((x - mn) ** 2 for x in new_dist[:n]) / n
    cov = sum((old_dist[i] - mo) * (new_dist[i] - mn) for i in range(n)) / n

    if var_o == 0 or var_n == 0:
        return 0.0

    rho = cov / (math.sqrt(var_o) * math.sqrt(var_n))
    rho = max(-0.999, min(0.999, rho))
    return -0.5 * math.log(1.0 - rho * rho)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _hopfield_energy(weight_matrix: list[list[float]], patterns: list[list[float]]) -> float:
    """E = -½ · Σᵢⱼ wᵢⱼ · sᵢ · sⱼ summed over all pattern pairs."""
    n = len(patterns)
    if n < 2:
        return 0.0

    energy = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            w = weight_matrix[i][j]
            # sᵢ · sⱼ = dot product of binary sign patterns
            si_sj = sum(
                (1.0 if a >= 0 else -1.0) * (1.0 if b >= 0 else -1.0)
                for a, b in zip(patterns[i], patterns[j])
            ) / max(len(patterns[i]), 1)
            energy -= w * si_sj

    return energy * 0.5


def _entry_to_vector(entry: dict) -> list[float]:
    """Convert entry to numerical vector for Hopfield patterns."""
    emb = entry.get("prompt_embedding")
    if emb is not None:
        return emb

    # Fallback: hash tokens to pseudo-embedding
    tokens = _tokenize(entry.get("content", ""))
    if not tokens:
        return [0.0]
    vec = [0.0] * 16
    for t in tokens:
        h = hash(t) % 16
        vec[h] += 1.0
    return vec


def compute_consolidation(
    entries: list[dict],
    gamma: float = 0.1,
    stable_threshold: float = 0.7,
    fragile_threshold: float = 0.3,
) -> Optional[ConsolidationResult]:
    """Compute memory consolidation scores.

    ConsolidationScore = MI(R_old, R_new) / H(R_old) · exp(-γ · Hopfield_energy)

    Args:
        entries: list of dicts with id, content, optional prompt_embedding,
                 source_trust, timestamp_age_days
        gamma: interference decay constant (default 0.1)
        stable_threshold: score above this = stable (default 0.7)
        fragile_threshold: score below this = fragile (default 0.3)

    Returns:
        ConsolidationResult or None on error
    """
    if not entries:
        return None

    try:
        n = len(entries)
        vectors = [_entry_to_vector(e) for e in entries]

        # Build Hopfield weight matrix from pairwise similarity
        W = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                sim = _cosine(vectors[i], vectors[j])
                W[i][j] = sim
                W[j][i] = sim

        # Hopfield energy
        hop_energy = _hopfield_energy(W, vectors)

        # Per-entry consolidation
        scores: list[EntryConsolidation] = []
        for idx, e in enumerate(entries):
            # R_old proxy: use source_trust and age-based decay
            trust = e.get("source_trust", 0.9)
            age = e.get("timestamp_age_days", 0)
            age_decay = math.exp(-age / 100.0)

            # Old distribution proxy
            old_dist = [trust, 1.0 - trust, age_decay, 1.0 - age_decay]
            # New distribution: current vector stats
            v = vectors[idx]
            v_abs = [abs(x) for x in v]
            new_dist = v_abs[:4] if len(v_abs) >= 4 else v_abs + [0.0] * (4 - len(v_abs))

            # Mutual information
            mi = _mutual_information(old_dist, new_dist)
            # Shannon entropy of old
            h_old = _shannon_entropy(old_dist)

            # Consolidation score
            if h_old > 0.01:
                mi_ratio = min(1.0, mi / h_old)
            else:
                mi_ratio = 1.0  # low entropy = highly concentrated = stable

            exp_term = math.exp(-gamma * abs(hop_energy))
            score = round(min(1.0, max(0.0, mi_ratio * exp_term)), 4)

            scores.append(EntryConsolidation(
                entry_id=e["id"],
                consolidation_score=score,
                stable=score > stable_threshold,
            ))

        mean_score = round(sum(s.consolidation_score for s in scores) / max(len(scores), 1), 4)
        fragile = [s.entry_id for s in scores if s.consolidation_score < fragile_threshold]
        replay = [s.entry_id for s in sorted(scores, key=lambda x: x.consolidation_score)]

        return ConsolidationResult(
            scores=scores,
            mean_consolidation=mean_score,
            fragile_entries=fragile,
            replay_priority=replay,
        )
    except Exception:
        return None
