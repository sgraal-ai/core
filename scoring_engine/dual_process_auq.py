from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class DualProcessResult:
    system1_uncertainty: float
    system2_uncertainty: float
    dual_process_uncertainty: float
    verbalized: str

def compute_dual_process(omega: float, surprise: float = 0.0, heavy_tail: bool = False, hmm_prob: float = 1.0, p_changepoint: float = 0.0, stability: float = 1.0) -> DualProcessResult:
    s1 = omega / 100.0
    signals = [surprise, 1.0 if heavy_tail else 0.0, 1.0 - hmm_prob, p_changepoint, 1.0 - stability]
    s2 = sum(signals) / max(len(signals), 1)
    dual = 0.3 * s1 + 0.7 * s2
    dual = round(min(1.0, max(0.0, dual)), 4)
    if dual < 0.3: v = "low uncertainty — safe to proceed"
    elif dual < 0.6: v = "moderate uncertainty — proceed with caution"
    else: v = "high uncertainty — human review recommended"
    return DualProcessResult(system1_uncertainty=round(s1, 4), system2_uncertainty=round(s2, 4), dual_process_uncertainty=dual, verbalized=v)
