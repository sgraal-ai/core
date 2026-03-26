from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional

@dataclass
class PoissonRecallResult:
    lambda_rate: float
    expected_errors_10: float
    error_probability: float

def compute_poisson_recall(lambda_rate: float = 0.1) -> Optional[PoissonRecallResult]:
    try:
        lam = max(0.0, lambda_rate)
        expected = lam * 10
        prob = 1.0 - math.exp(-lam * 10)
        return PoissonRecallResult(lambda_rate=round(lam, 4), expected_errors_10=round(expected, 4), error_probability=round(prob, 4))
    except Exception:
        return None
