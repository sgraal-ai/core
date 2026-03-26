from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class CVaRResult:
    var_5: float
    cvar_5: float
    tail_risk: str

def compute_cvar(score_history: list[float], alpha: float = 0.05, min_observations: int = 10) -> Optional[CVaRResult]:
    if len(score_history) < min_observations:
        return None
    try:
        s = sorted(score_history)
        n = len(s)
        idx = max(0, int(n * alpha) - 1)
        var_5 = s[idx]
        tail = [x for x in s if x <= var_5]
        if not tail:
            tail = [s[0]]
        cvar = sum(tail) / len(tail)
        if cvar < 30:
            risk = "low"
        elif cvar <= 60:
            risk = "medium"
        else:
            risk = "high"
        return CVaRResult(var_5=round(var_5, 4), cvar_5=round(cvar, 4), tail_risk=risk)
    except Exception:
        return None
