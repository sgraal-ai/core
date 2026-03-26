from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class EntryProvenance:
    entry_id: str
    entropy: float
    source_count: int
    conflict_probable: bool


@dataclass
class ProvenanceEntropyResult:
    per_entry: list[EntryProvenance]
    mean_entropy: float
    high_entropy_entries: list[str]
    entropy_trend: str  # "stable", "increasing", "decreasing", "unknown"


def _shannon_entropy(weights: list[float]) -> float:
    """H = -Σ pᵢ · log(pᵢ) over normalized weights."""
    total = sum(weights) or 1.0
    probs = [w / total for w in weights if w > 0]
    if len(probs) <= 1:
        return 0.0
    return -sum(p * math.log(p + 1e-10) for p in probs)


def compute_provenance_entropy(
    entries: list[dict],
    conflict_threshold: float = 1.0,
    history: Optional[list[float]] = None,
) -> Optional[ProvenanceEntropyResult]:
    """Shannon entropy on provenance graph for source heterogeneity.

    H = -Σ pᵢ · log(pᵢ) where pᵢ = normalized source_trust weights.

    High entropy = many equally weighted sources = higher conflict probability.
    Low entropy = one dominant source = more trustworthy.

    Args:
        entries: list of dicts with id, source_trust
        conflict_threshold: entropy above this = conflict_probable (default 1.0)
        history: recent mean_entropy values for trend detection

    Returns:
        ProvenanceEntropyResult or None if no entries
    """
    if not entries:
        return None

    try:
        # Collect all source_trust values as the "provenance distribution"
        all_trusts = [e.get("source_trust", 0.5) for e in entries]

        per_entry = []
        high_entropy = []

        for e in entries:
            trust = e.get("source_trust", 0.5)
            conflict = e.get("source_conflict", 0.1) if e.get("source_conflict") is not None else 0.1

            # Per-entry: entropy over [trust, 1-trust, conflict, 1-conflict]
            # This captures the uncertainty in each entry's provenance
            weights = [trust, 1.0 - trust, conflict, 1.0 - conflict]
            weights = [w for w in weights if w > 0]
            h = round(_shannon_entropy(weights), 4)

            source_count = len([w for w in weights if w > 0.01])
            conflict_probable = h > conflict_threshold

            eid = e.get("id", "unknown")
            per_entry.append(EntryProvenance(
                entry_id=eid,
                entropy=h,
                source_count=source_count,
                conflict_probable=conflict_probable,
            ))

            if conflict_probable:
                high_entropy.append(eid)

        # Global entropy: over all source_trust values across entries
        global_h = round(_shannon_entropy(all_trusts), 4)
        mean_h = round(sum(pe.entropy for pe in per_entry) / max(len(per_entry), 1), 4)

        # Entropy trend from history
        trend = "unknown"
        if history and len(history) >= 2:
            recent = history[-3:] if len(history) >= 3 else history
            diffs = [recent[i + 1] - recent[i] for i in range(len(recent) - 1)]
            avg_diff = sum(diffs) / len(diffs)
            if avg_diff > 0.05:
                trend = "increasing"
            elif avg_diff < -0.05:
                trend = "decreasing"
            else:
                trend = "stable"

        return ProvenanceEntropyResult(
            per_entry=per_entry,
            mean_entropy=mean_h,
            high_entropy_entries=high_entropy,
            entropy_trend=trend,
        )
    except Exception:
        return None
