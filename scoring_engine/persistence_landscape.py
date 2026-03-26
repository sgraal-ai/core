from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional

@dataclass
class PersistenceLandscapeResult:
    landscape_values: list[float]
    landscape_norm: float
    topology_complexity: float

def compute_persistence_landscape(betti_1_data: Optional[list[dict]] = None) -> Optional[PersistenceLandscapeResult]:
    if not betti_1_data:
        return None
    try:
        values = [b.get("count", 0) for b in betti_1_data]
        while len(values) < 6:
            values.append(0)
        values = values[:6]
        norm = math.sqrt(sum(v * v for v in values))
        complexity = sum(values) / max(len(values), 1)
        return PersistenceLandscapeResult(landscape_values=[round(v, 4) for v in values], landscape_norm=round(norm, 4), topology_complexity=round(complexity, 4))
    except Exception:
        return None
