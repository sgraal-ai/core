from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class LQRResult:
    optimal_control: float
    state_deviation: float
    control_effort: float
    target_omega: float

def compute_lqr(omega: float, target: float = 50.0, Q: float = 1.0, R: float = 0.1) -> Optional[LQRResult]:
    try:
        K = Q / (R + Q)
        deviation = omega - target
        u = -K * deviation
        effort = abs(u)
        return LQRResult(optimal_control=round(u, 4), state_deviation=round(deviation, 4), control_effort=round(effort, 4), target_omega=target)
    except Exception:
        return None
