from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BLOCK_THRESHOLD = 80.0


@dataclass
class ForecastResult:
    trend: Literal["improving", "stable", "degrading"]
    collapse_risk: float  # 0.0–1.0, probability of hitting BLOCK threshold
    forecast_scores: list[float]


class KalmanForecaster:
    """Simple 1D Kalman filter for Ω_MEM score trend forecasting."""

    def __init__(
        self,
        process_noise: float = 0.1,
        measurement_noise: float = 1.0,
    ):
        self.Q = process_noise
        self.R = measurement_noise
        self._state: float = 0.0
        self._covariance: float = 1.0
        self._velocity: float = 0.0
        self._fitted = False

    def fit(self, history: list[float]) -> None:
        """Fit the Kalman filter on a sequence of omega_mem_final scores."""
        if len(history) < 2:
            self._state = history[0] if history else 0.0
            self._velocity = 0.0
            self._covariance = 1.0
            self._fitted = True
            return

        # Initialize state from first observation
        self._state = history[0]
        self._covariance = 1.0
        self._velocity = 0.0

        prev_state = history[0]

        for measurement in history[1:]:
            # Predict
            predicted_state = self._state + self._velocity
            predicted_cov = self._covariance + self.Q

            # Update
            innovation = measurement - predicted_state
            kalman_gain = predicted_cov / (predicted_cov + self.R)
            self._state = predicted_state + kalman_gain * innovation
            self._covariance = (1 - kalman_gain) * predicted_cov

            # Track velocity (smoothed slope)
            self._velocity = 0.7 * self._velocity + 0.3 * (self._state - prev_state)
            prev_state = self._state

        self._fitted = True

    def predict(self, steps: int = 5) -> ForecastResult:
        """Forecast next N scores and compute trend + collapse risk."""
        if not self._fitted:
            return ForecastResult(
                trend="stable",
                collapse_risk=0.0,
                forecast_scores=[],
            )

        # Generate forecasts
        forecasts: list[float] = []
        state = self._state
        for _ in range(steps):
            state = state + self._velocity
            forecasts.append(round(max(0.0, min(100.0, state)), 1))

        # Determine trend from velocity
        if self._velocity > 0.5:
            trend: Literal["improving", "stable", "degrading"] = "degrading"
        elif self._velocity < -0.5:
            trend = "improving"
        else:
            trend = "stable"

        # Collapse risk: proportion of forecast steps that exceed BLOCK threshold
        above_block = sum(1 for s in forecasts if s >= BLOCK_THRESHOLD)
        collapse_risk = round(above_block / max(len(forecasts), 1), 2)

        return ForecastResult(
            trend=trend,
            collapse_risk=collapse_risk,
            forecast_scores=forecasts,
        )
