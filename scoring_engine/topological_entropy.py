from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional

@dataclass
class TopologicalEntropyResult:
    entropy_estimate: float
    distinct_states_visited: int
    complexity_class: str

def compute_topological_entropy(score_history: list[float], current_score: float, min_observations: int = 10) -> Optional[TopologicalEntropyResult]:
    if len(score_history) < min_observations:
        return None
    try:
        all_scores = score_history + [current_score]
        n = len(all_scores)
        bins = set()
        for s in all_scores:
            if s <= 25: bins.add(0)
            elif s <= 50: bins.add(1)
            elif s <= 75: bins.add(2)
            else: bins.add(3)
        distinct = len(bins)
        h = math.log(max(distinct, 1)) / max(math.log(n), 1)
        if h < 0.5: cls = "ordered"
        elif h <= 1.0: cls = "complex"
        else: cls = "chaotic"
        return TopologicalEntropyResult(entropy_estimate=round(h, 4), distinct_states_visited=distinct, complexity_class=cls)
    except Exception:
        return None
