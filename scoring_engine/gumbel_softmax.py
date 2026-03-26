from __future__ import annotations
import math, hashlib
from dataclasses import dataclass
from typing import Optional

ACTIONS = ["USE_MEMORY", "WARN", "ASK_USER", "BLOCK"]

@dataclass
class GumbelSoftmaxResult:
    relaxed_probs: dict[str, float]
    temperature: float
    straight_through: bool

def _gumbel_sample(seed: str, idx: int) -> float:
    h = int(hashlib.sha256(f"{seed}:{idx}".encode()).hexdigest()[:8], 16)
    u = (h % 10000 + 1) / 10001.0
    return -math.log(-math.log(u + 1e-10) + 1e-10)

def compute_gumbel_softmax(log_probs: list[float], temperature: float = 1.0, seed: str = "default") -> Optional[GumbelSoftmaxResult]:
    if len(log_probs) != 4:
        return None
    try:
        tau = max(temperature, 0.01)
        gumbels = [_gumbel_sample(seed, i) for i in range(4)]
        scaled = [(log_probs[i] + gumbels[i]) / tau for i in range(4)]
        max_s = max(scaled)
        exps = [math.exp(s - max_s) for s in scaled]
        total = sum(exps)
        probs = {ACTIONS[i]: round(exps[i] / total, 4) for i in range(4)}
        return GumbelSoftmaxResult(relaxed_probs=probs, temperature=round(tau, 4), straight_through=tau < 0.5)
    except Exception:
        return None
