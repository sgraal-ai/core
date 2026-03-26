from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class ROCResult:
    auc_estimate: float
    model_degraded: bool
    retrain_recommended: bool

def compute_roc_auc(predictions: list[float], actuals: list[float]) -> Optional[ROCResult]:
    n = len(predictions)
    if n < 10 or len(actuals) != n:
        return None
    try:
        pairs = list(zip(predictions, actuals))
        pairs.sort(key=lambda x: -x[0])
        tp, fp, prev_tp, prev_fp = 0, 0, 0, 0
        auc = 0.0
        n_pos = sum(1 for _, a in pairs if a > 0.5)
        n_neg = n - n_pos
        if n_pos == 0 or n_neg == 0:
            return ROCResult(auc_estimate=0.5, model_degraded=False, retrain_recommended=False)
        for _, actual in pairs:
            if actual > 0.5:
                tp += 1
            else:
                fp += 1
                auc += tp
        auc = auc / (n_pos * n_neg) if n_pos * n_neg > 0 else 0.5
        degraded = auc < 0.7
        retrain = degraded and n > 20
        return ROCResult(auc_estimate=round(auc, 4), model_degraded=degraded, retrain_recommended=retrain)
    except Exception:
        return None
