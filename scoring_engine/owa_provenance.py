from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class OWAResult:
    owa_score: float
    weights_used: list[float]
    orness: float

def compute_owa(trust_scores: list[float]) -> Optional[OWAResult]:
    if not trust_scores:
        return None
    try:
        n = len(trust_scores)
        sorted_desc = sorted(trust_scores, reverse=True)
        denom = sum(range(1, n + 1))
        weights = [(n - i) / denom for i in range(n)]
        owa = sum(weights[i] * sorted_desc[i] for i in range(n))
        if n > 1:
            orness = sum((n - 1 - i) * weights[i] for i in range(n)) / (n - 1)
        else:
            orness = 1.0
        return OWAResult(owa_score=round(owa, 4), weights_used=[round(w, 4) for w in weights], orness=round(orness, 4))
    except Exception:
        return None
