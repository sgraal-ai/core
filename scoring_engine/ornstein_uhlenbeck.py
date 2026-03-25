from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class OUResult:
    theta: float          # mean-reversion speed
    mu: float             # long-term mean
    sigma: float          # volatility
    half_life: float      # time to revert halfway: ln(2)/θ
    current_deviation: float  # X_t - μ
    expected_value_5: float   # E[X_{t+5}]
    expected_value_10: float  # E[X_{t+10}]
    mean_reverting: bool      # true when θ > 0.01


def compute_ou_process(
    score_history: list[float],
    current_score: float,
    min_observations: int = 10,
) -> Optional[OUResult]:
    """Ornstein-Uhlenbeck mean-reversion process for recovery prediction.

    dX = θ(μ - X)dt + σdW

    where:
        θ = mean-reversion speed (how fast X returns to μ)
        μ = long-term mean (equilibrium level)
        σ = volatility (diffusion coefficient)

    Parameter estimation via OLS on discrete OU:
        X_{t+1} - X_t = θ(μ - X_t)Δt + σ√Δt · ε_t
        ΔX_t = a + b·X_t + noise  →  θ = -b, μ = -a/b

    Conditional expectation:
        E[X_{t+s} | X_t] = μ + (X_t - μ)·exp(-θ·s)

    Half-life: t_{1/2} = ln(2) / θ

    Args:
        score_history: past omega_mem_final scores (oldest first)
        current_score: current omega_mem_final score
        min_observations: minimum history length (default 10)

    Returns:
        OUResult or None if insufficient history or estimation fails
    """
    if len(score_history) < min_observations:
        return None

    try:
        all_scores = score_history + [current_score]
        n = len(all_scores) - 1  # number of transitions

        if n < 3:
            return None

        # Compute ΔX_t = X_{t+1} - X_t and pair with X_t
        # OLS regression: ΔX_t = a + b·X_t
        x_vals = all_scores[:-1]  # X_t
        dx_vals = [all_scores[i + 1] - all_scores[i] for i in range(n)]  # ΔX_t

        # OLS: ΔX = a + b·X
        mean_x = sum(x_vals) / n
        mean_dx = sum(dx_vals) / n

        ss_xx = sum((x - mean_x) ** 2 for x in x_vals)
        ss_xdx = sum((x_vals[i] - mean_x) * (dx_vals[i] - mean_dx) for i in range(n))

        if ss_xx < 1e-12:
            return None  # degenerate: all scores identical

        b = ss_xdx / ss_xx
        a = mean_dx - b * mean_x

        # θ = -b (mean-reversion speed, should be positive for mean-reverting)
        theta = -b

        # μ = -a/b (long-term mean)
        if abs(b) < 1e-12:
            # No mean reversion detected, use sample mean
            mu = sum(all_scores) / len(all_scores)
            theta = 0.0
        else:
            mu = -a / b

        # Clamp theta to reasonable range
        theta = max(0.0, min(theta, 10.0))

        # σ estimation from residuals
        # Residuals: ε_t = ΔX_t - (a + b·X_t)
        residuals = [dx_vals[i] - (a + b * x_vals[i]) for i in range(n)]
        res_var = sum(r * r for r in residuals) / max(n - 2, 1)
        sigma = math.sqrt(max(res_var, 0.0))

        # Half-life: ln(2) / θ
        if theta > 0.001:
            half_life = round(math.log(2) / theta, 2)
        else:
            half_life = round(1000.0, 2)  # effectively non-reverting

        # Current deviation from equilibrium
        current_deviation = round(current_score - mu, 4)

        # Conditional expectation: E[X_{t+s}] = μ + (X_t - μ)·exp(-θ·s)
        dev = current_score - mu
        expected_5 = round(mu + dev * math.exp(-theta * 5), 4)
        expected_10 = round(mu + dev * math.exp(-theta * 10), 4)

        mean_reverting = theta > 0.01

        return OUResult(
            theta=round(theta, 4),
            mu=round(mu, 4),
            sigma=round(sigma, 4),
            half_life=half_life,
            current_deviation=current_deviation,
            expected_value_5=expected_5,
            expected_value_10=expected_10,
            mean_reverting=mean_reverting,
        )
    except Exception:
        return None
