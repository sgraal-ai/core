from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Opinion:
    belief: float
    disbelief: float
    uncertainty: float
    projected_prob: float


@dataclass
class SubjectiveLogicResult:
    opinions: list[tuple[str, Opinion]]  # (entry_id, opinion)
    fused_opinion: Optional[Opinion]
    high_uncertainty_entries: list[str]
    consensus_possible: bool


def _make_opinion(
    source_trust: float,
    source_conflict: float,
    base_rate: float = 0.5,
) -> Opinion:
    """Build subjective logic opinion B = {b, d, u, a}.

    b = belief = source_trust
    d = disbelief = source_conflict
    u = 1.0 - b - d (uncertainty)
    a = base_rate (uninformed prior, default 0.5)
    P(X) = b + a·u
    """
    b = max(0.0, source_trust)
    d = max(0.0, source_conflict)

    # Clip if b + d > 1.0
    total = b + d
    if total > 1.0:
        logger.warning("source values exceed unit constraint: trust=%.3f conflict=%.3f", b, d)
        b = b / total
        d = d / total
        u = 0.0
    else:
        u = 1.0 - b - d

    # Safety clamp
    u = max(0.0, u)

    projected = round(b + base_rate * u, 4)

    return Opinion(
        belief=round(b, 4),
        disbelief=round(d, 4),
        uncertainty=round(u, 4),
        projected_prob=projected,
    )


def _fuse_two(o1: Opinion, o2: Opinion, base_rate: float = 0.5) -> Optional[Opinion]:
    """Cumulative fusion of two opinions.

    b_f = (b₁·u₂ + b₂·u₁) / (u₁ + u₂ - u₁·u₂)
    d_f = (d₁·u₂ + d₂·u₁) / (u₁ + u₂ - u₁·u₂)
    u_f = (u₁·u₂) / (u₁ + u₂ - u₁·u₂)
    """
    denom = o1.uncertainty + o2.uncertainty - o1.uncertainty * o2.uncertainty

    if abs(denom) < 1e-10:
        return None  # division by zero guard

    b_f = (o1.belief * o2.uncertainty + o2.belief * o1.uncertainty) / denom
    d_f = (o1.disbelief * o2.uncertainty + o2.disbelief * o1.uncertainty) / denom
    u_f = (o1.uncertainty * o2.uncertainty) / denom

    # Clamp
    b_f = max(0.0, min(1.0, b_f))
    d_f = max(0.0, min(1.0, d_f))
    u_f = max(0.0, min(1.0, u_f))

    # Renormalize if needed
    total = b_f + d_f + u_f
    if total > 0:
        b_f /= total
        d_f /= total
        u_f /= total

    projected = round(b_f + base_rate * u_f, 4)

    return Opinion(
        belief=round(b_f, 4),
        disbelief=round(d_f, 4),
        uncertainty=round(u_f, 4),
        projected_prob=projected,
    )


def compute_subjective_logic(
    entries: list[dict],
    base_rate: float = 0.5,
    uncertainty_threshold: float = 0.3,
    consensus_threshold: float = 0.2,
) -> Optional[SubjectiveLogicResult]:
    """Subjective Logic for explicit uncertainty handling in source trust.

    Args:
        entries: list of dicts with id, source_trust, source_conflict
        base_rate: uninformed prior a (default 0.5)
        uncertainty_threshold: u above this = high uncertainty (default 0.3)
        consensus_threshold: fused u below this = consensus possible (default 0.2)

    Returns:
        SubjectiveLogicResult or None if no entries
    """
    if not entries:
        return None

    try:
        opinions: list[tuple[str, Opinion]] = []
        high_uncertainty: list[str] = []

        for e in entries:
            eid = e.get("id", "unknown")
            trust = e.get("source_trust", 0.5)
            conflict = e.get("source_conflict", 0.1) if e.get("source_conflict") is not None else 0.1

            op = _make_opinion(trust, conflict, base_rate)
            opinions.append((eid, op))

            if op.uncertainty > uncertainty_threshold:
                high_uncertainty.append(eid)

        # Fuse all opinions sequentially
        fused = None
        if len(opinions) == 1:
            fused = opinions[0][1]
        elif len(opinions) >= 2:
            fused = opinions[0][1]
            for i in range(1, len(opinions)):
                fused = _fuse_two(fused, opinions[i][1], base_rate)
                if fused is None:
                    break  # division by zero, stop fusion

        consensus = fused is not None and fused.uncertainty < consensus_threshold

        return SubjectiveLogicResult(
            opinions=opinions,
            fused_opinion=fused,
            high_uncertainty_entries=high_uncertainty,
            consensus_possible=consensus,
        )
    except Exception:
        return None
