from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class JumpDiffusionResult:
    jump_detected: bool
    jump_size: float
    jump_rate_lambda: float
    diffusion_sigma: float
    flash_crash_risk: bool
    expected_next_jump: float


def compute_jump_diffusion(
    score_history: list[float],
    current_score: float,
    min_observations: int = 5,
) -> Optional[JumpDiffusionResult]:
    """Detect sudden memory state changes via Jump-Diffusion model.

    dX = f(X,μ)dt + σdW + J·dN(t)

    where:
        f(X,μ)dt = drift (EWMA trend)
        σdW = Gaussian diffusion (normal volatility)
        J = jump size (sudden change magnitude)
        dN(t) = Poisson process with rate λ (jump arrival rate)

    Parameters estimated from omega_mem_final history:
        σ = std(normal_changes) where |change| < 2σ
        λ = count(|change| > 3σ) / n_observations
        J = mean(|change|) for jumps above 3σ threshold

    Args:
        score_history: past omega_mem_final scores (oldest first)
        current_score: current omega_mem_final score
        min_observations: minimum history length required (default 5)

    Returns:
        JumpDiffusionResult or None if insufficient history
    """
    if len(score_history) < min_observations:
        return None

    try:
        # Compute changes between consecutive observations
        all_scores = score_history + [current_score]
        changes = [all_scores[i + 1] - all_scores[i] for i in range(len(all_scores) - 1)]
        n = len(changes)

        if n < 2:
            return None

        # Robust σ estimation via Median Absolute Deviation (MAD)
        # MAD is resistant to outliers unlike mean/variance
        sorted_changes = sorted(changes)
        median_change = sorted_changes[n // 2] if n % 2 == 1 else (sorted_changes[n // 2 - 1] + sorted_changes[n // 2]) / 2
        abs_devs = sorted(abs(c - median_change) for c in changes)
        mad = abs_devs[len(abs_devs) // 2] if len(abs_devs) % 2 == 1 else (abs_devs[len(abs_devs) // 2 - 1] + abs_devs[len(abs_devs) // 2]) / 2

        # σ_MAD = 1.4826 · MAD (consistent estimator for Gaussian σ)
        # When MAD=0 (all changes identical or near-identical), fall back to IQR-based estimate
        if mad > 0:
            sigma = 1.4826 * mad
        else:
            # IQR / 1.35 as fallback robust σ estimator
            q1 = sorted_changes[n // 4] if n >= 4 else sorted_changes[0]
            q3 = sorted_changes[3 * n // 4] if n >= 4 else sorted_changes[-1]
            iqr = q3 - q1
            sigma = iqr / 1.35 if iqr > 0 else max(abs(sorted_changes[-1] - sorted_changes[0]) / 4, 1e-6)

        # Identify jumps: |change - median| > 3σ
        jump_threshold = 3 * sigma
        jumps = [c for c in changes if abs(c - median_change) > jump_threshold]
        n_jumps = len(jumps)

        # Jump rate λ = count(jumps) / n_observations
        jump_rate_lambda = round(n_jumps / n, 4) if n > 0 else 0.0

        # Mean jump size J = mean(|change|) for jumps
        mean_jump_size = round(sum(abs(j) for j in jumps) / n_jumps, 4) if n_jumps > 0 else 0.0

        # Current change (last observation)
        current_change = changes[-1]
        jump_detected = abs(current_change - median_change) > jump_threshold

        # Jump size for current observation
        jump_size = round(abs(current_change), 4) if jump_detected else 0.0

        # Flash crash risk: λ > 0.1 (more than 10% of observations are jumps)
        flash_crash_risk = jump_rate_lambda > 0.1

        # Expected time to next jump: E[T] = 1/λ (Poisson inter-arrival)
        # Expressed as number of observations until next expected jump
        if jump_rate_lambda > 0.001:
            expected_next_jump = round(1.0 / jump_rate_lambda, 2)
        else:
            expected_next_jump = round(1000.0, 2)  # effectively no jumps expected

        return JumpDiffusionResult(
            jump_detected=jump_detected,
            jump_size=jump_size,
            jump_rate_lambda=jump_rate_lambda,
            diffusion_sigma=round(sigma, 4),
            flash_crash_risk=flash_crash_risk,
            expected_next_jump=expected_next_jump,
        )
    except Exception:
        return None
