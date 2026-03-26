from __future__ import annotations
import math, hashlib
from dataclasses import dataclass
from typing import Optional

@dataclass
class SAResult:
    current_temperature: float
    accepted_moves: int
    best_loss: float
    sa_active: bool

def compute_simulated_annealing(current_loss: float, geodesic_count: int, previous_state: Optional[dict] = None, T0: float = 1.0, cooling: float = 0.95, max_iter: int = 50) -> Optional[SAResult]:
    if geodesic_count < 20:
        return SAResult(current_temperature=T0, accepted_moves=0, best_loss=current_loss, sa_active=False)
    try:
        if previous_state:
            temp = previous_state.get("temperature", T0)
            accepted = previous_state.get("accepted", 0)
            best = previous_state.get("best_loss", current_loss)
            iteration = previous_state.get("iteration", 0) + 1
        else:
            temp, accepted, best, iteration = T0, 0, current_loss, 0
        if iteration >= max_iter:
            return SAResult(current_temperature=round(temp, 4), accepted_moves=accepted, best_loss=round(best, 4), sa_active=False)
        temp = T0 * (cooling ** iteration)
        delta = current_loss - best
        if delta < 0:
            accepted += 1
            best = current_loss
        elif temp > 1e-10:
            h = int(hashlib.sha256(f"sa:{iteration}:{current_loss}".encode()).hexdigest()[:8], 16)
            u = (h % 10000) / 10000.0
            if u < math.exp(-delta / temp):
                accepted += 1
        return SAResult(current_temperature=round(temp, 4), accepted_moves=accepted, best_loss=round(best, 4), sa_active=True)
    except Exception:
        return None
