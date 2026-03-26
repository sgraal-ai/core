from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional

@dataclass
class CoxHazardResult:
    hazard_rate: float
    survival_probability: float
    high_risk: bool

def compute_cox_hazard(entries: list[dict], h0: float = 0.01, betas: list[float] = None) -> Optional[CoxHazardResult]:
    if not entries:
        return None
    try:
        if betas is None:
            betas = [0.3, 0.2, 0.1]
        hazards = []
        for e in entries:
            x = [e.get("source_trust", 0.5), e.get("downstream_count", 0) / 10.0, e.get("timestamp_age_days", 0) / 100.0]
            linear = sum(betas[i] * x[i] for i in range(min(len(betas), len(x))))
            h = h0 * math.exp(linear)
            hazards.append(h)
        mean_h = sum(hazards) / len(hazards)
        surv = math.exp(-mean_h * 10)
        return CoxHazardResult(hazard_rate=round(mean_h, 4), survival_probability=round(surv, 4), high_risk=mean_h > 0.1)
    except Exception:
        return None
