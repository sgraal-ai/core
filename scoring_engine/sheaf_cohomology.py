from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConsistencyResult:
    consistency_score: float       # 1 - (h1_rank / max_possible_rank), 0–1
    h1_rank: int                   # 0 = globally consistent
    inconsistent_pairs: list[tuple[str, str]]
    auto_source_conflict: float    # 0–1, replaces manual source_conflict


def _tokenize(text: str) -> set[str]:
    """Simple whitespace + lowercase tokenizer."""
    return set(text.lower().split())


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    """Jaccard similarity J(A,B) = |A∩B| / |A∪B|."""
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two embedding vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _content_overlap(tokens_a: set[str], tokens_b: set[str]) -> float:
    """Content overlap score for determining if two entries share a topic."""
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / min(len(tokens_a), len(tokens_b))


def compute_sheaf_consistency(
    entries: list[dict],
    consistency_threshold: float = 0.7,
    overlap_threshold: float = 0.15,
    max_pairs: int = 190,  # C(20,2) = 190, keeps <5ms for 20 entries
) -> ConsistencyResult:
    """Build sheaf over memory entries and compute H¹ cohomology.

    Sheaf construction:
    - Nodes: memory entries
    - Edges: entries with content overlap > overlap_threshold
    - Local consistency: cosine similarity of embeddings (or Jaccard fallback)
    - H¹ rank: number of inconsistent edges (cycles where local sections disagree)

    Args:
        entries: list of dicts with id, content, and optional prompt_embedding
        consistency_threshold: similarity above this = consistent (default 0.7)
        overlap_threshold: minimum content overlap to create an edge (default 0.15)
        max_pairs: maximum pairs to check (performance bound)

    Returns:
        ConsistencyResult with consistency_score, h1_rank, inconsistent_pairs,
        and auto_source_conflict
    """
    n = len(entries)

    if n <= 1:
        return ConsistencyResult(
            consistency_score=1.0,
            h1_rank=0,
            inconsistent_pairs=[],
            auto_source_conflict=0.0,
        )

    # Tokenize all entries
    tokens = [_tokenize(e.get("content", "")) for e in entries]
    embeddings = [e.get("prompt_embedding") for e in entries]

    # Build edges: pairs with content overlap
    edges: list[tuple[int, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            if len(edges) >= max_pairs:
                break
            overlap = _content_overlap(tokens[i], tokens[j])
            if overlap >= overlap_threshold:
                edges.append((i, j))

    if not edges:
        return ConsistencyResult(
            consistency_score=1.0,
            h1_rank=0,
            inconsistent_pairs=[],
            auto_source_conflict=0.0,
        )

    # Check local consistency on each edge
    inconsistent: list[tuple[str, str]] = []
    for i, j in edges:
        # Prefer embedding cosine similarity, fall back to Jaccard
        emb_i, emb_j = embeddings[i], embeddings[j]
        if emb_i is not None and emb_j is not None and len(emb_i) == len(emb_j):
            sim = _cosine_similarity(emb_i, emb_j)
        else:
            sim = _jaccard_similarity(tokens[i], tokens[j])

        if sim < consistency_threshold:
            inconsistent.append((entries[i]["id"], entries[j]["id"]))

    # H¹ rank = number of inconsistent edges (obstructions to global section)
    h1_rank = len(inconsistent)
    max_rank = max(len(edges), 1)
    consistency_score = round(1.0 - (h1_rank / max_rank), 4)

    # Auto source conflict: proportion of inconsistent edges, scaled to 0–1
    auto_conflict = round(h1_rank / max_rank, 4) if max_rank > 0 else 0.0

    return ConsistencyResult(
        consistency_score=consistency_score,
        h1_rank=h1_rank,
        inconsistent_pairs=inconsistent,
        auto_source_conflict=auto_conflict,
    )
