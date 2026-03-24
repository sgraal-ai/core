from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class TrendResult:
    cusum_alert: bool
    ewma_alert: bool
    drift_sustained: bool
    consecutive_degradations: int
    cusum_pos: float
    cusum_neg: float
    ewma_value: float


class CUSUMDetector:
    """Cumulative Sum (CUSUM) change detection.

    S⁺ₜ = max(0, S⁺ₜ₋₁ + zₜ - k)
    S⁻ₜ = max(0, S⁻ₜ₋₁ - zₜ - k)

    Alert when S⁺ or S⁻ exceeds threshold h.
    """

    def __init__(self, k: float = 0.5, h: float = 5.0):
        self.k = k  # allowance (slack) parameter
        self.h = h  # decision threshold

    def detect(self, values: list[float], target: float | None = None) -> tuple[bool, float, float]:
        """Run CUSUM on a sequence of values.

        Args:
            values: time series of scores
            target: expected mean (default: mean of first half)

        Returns:
            (alert, S_pos, S_neg)
        """
        if len(values) < 2:
            return False, 0.0, 0.0

        if target is None:
            half = max(1, len(values) // 2)
            target = sum(values[:half]) / half

        s_pos = 0.0
        s_neg = 0.0
        alert = False

        for x in values:
            z = x - target
            s_pos = max(0.0, s_pos + z - self.k)
            s_neg = max(0.0, s_neg - z - self.k)
            if s_pos > self.h or s_neg > self.h:
                alert = True

        return alert, round(s_pos, 4), round(s_neg, 4)


class EWMADetector:
    """Exponentially Weighted Moving Average detector.

    Zₜ = λ·Xₜ + (1-λ)·Zₜ₋₁

    Alert when Zₜ deviates more than L·σ from baseline.
    """

    def __init__(self, lam: float = 0.2, L: float = 3.0):
        self.lam = lam  # smoothing parameter
        self.L = L      # control limit (number of σ)

    def detect(self, values: list[float]) -> tuple[bool, float]:
        """Run EWMA on a sequence of values.

        Args:
            values: time series of scores

        Returns:
            (alert, current_ewma)
        """
        if len(values) < 2:
            return False, values[0] if values else 0.0

        # Baseline: mean and std of first half
        half = max(1, len(values) // 2)
        baseline = values[:half]
        mu = sum(baseline) / len(baseline)
        variance = sum((x - mu) ** 2 for x in baseline) / max(len(baseline) - 1, 1)
        sigma = math.sqrt(variance) if variance > 0 else 1.0

        z = mu  # initialize EWMA at baseline mean
        alert = False

        for x in values:
            z = self.lam * x + (1 - self.lam) * z
            if abs(z - mu) > self.L * sigma:
                alert = True

        return alert, round(z, 4)


def detect_trend(
    history: list[float],
    cusum_k: float = 0.5,
    cusum_h: float = 5.0,
    ewma_lam: float = 0.2,
    ewma_L: float = 3.0,
) -> TrendResult:
    """Detect drift trends using CUSUM + EWMA ensemble.

    Args:
        history: list of omega_mem_final scores over time
        cusum_k: CUSUM allowance parameter
        cusum_h: CUSUM decision threshold
        ewma_lam: EWMA smoothing parameter
        ewma_L: EWMA control limit (σ multiplier)

    Returns:
        TrendResult with alerts and consecutive degradation count
    """
    if len(history) < 2:
        return TrendResult(
            cusum_alert=False, ewma_alert=False,
            drift_sustained=False, consecutive_degradations=0,
            cusum_pos=0.0, cusum_neg=0.0, ewma_value=history[0] if history else 0.0,
        )

    cusum = CUSUMDetector(k=cusum_k, h=cusum_h)
    ewma = EWMADetector(lam=ewma_lam, L=ewma_L)

    cusum_alert, s_pos, s_neg = cusum.detect(history)
    ewma_alert, ewma_val = ewma.detect(history)

    # Count consecutive degradations (score increasing = degrading)
    consec = 0
    max_consec = 0
    for i in range(1, len(history)):
        if history[i] > history[i - 1]:
            consec += 1
            max_consec = max(max_consec, consec)
        else:
            consec = 0

    # Drift sustained: 4+ consecutive degradations AND both detectors agree
    drift_sustained = max_consec >= 4 and cusum_alert and ewma_alert

    return TrendResult(
        cusum_alert=cusum_alert,
        ewma_alert=ewma_alert,
        drift_sustained=drift_sustained,
        consecutive_degradations=max_consec,
        cusum_pos=s_pos,
        cusum_neg=s_neg,
        ewma_value=ewma_val,
    )
