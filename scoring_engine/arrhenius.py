from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional

@dataclass
class ArrheniusResult:
    degradation_rate: float
    effective_lifetime: float
    heat_index: float

def compute_arrhenius(entries: list[dict], A: float = 1.0, Ea: float = 0.5, R: float = 0.1) -> Optional[ArrheniusResult]:
    if not entries:
        return None
    try:
        conflicts = [e.get("source_conflict", 0.0) or 0.0 for e in entries]
        heat = sum(conflicts) / len(conflicts)
        heat = max(heat, 0.01)
        k = A * math.exp(-Ea / (R * heat + 1e-8))
        lifetime = 1.0 / max(k, 1e-8)
        return ArrheniusResult(degradation_rate=round(k, 4), effective_lifetime=round(lifetime, 2), heat_index=round(heat, 4))
    except Exception:
        return None
