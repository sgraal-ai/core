from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class FreeEnergyResult:
    F: float              # Free energy = -ELBO
    elbo: float           # Evidence Lower Bound
    kl_divergence: float  # KL(q(z)||p(z))
    reconstruction: float # E_q[log p(x|z)] ≈ -MSE
    surprise: float       # F / max_observed_F, normalized 0-1


def compute_free_energy(
    omega_actual: float,
    meta_score: float,
    component_breakdown: dict,
    max_observed_F: Optional[float] = None,
) -> Optional[FreeEnergyResult]:
    """Compute variational Free Energy functional.

    F = E_q[log q(z) - log p(x,z)] = -ELBO
    ELBO = E_q[log p(x|z)] - KL(q(z)||p(z))

    Uses calibration.py logistic meta-layer (ML-06) as approximate posterior q(z).
    p(x|z) = likelihood of omega_mem_final given latent state z.
    p(z) = standard normal prior N(0,1).

    Args:
        omega_actual: actual omega_mem_final score
        meta_score: logistic meta-layer output (0-100) from calibration
        component_breakdown: dict of component scores
        max_observed_F: maximum F seen so far (for surprise normalization)

    Returns:
        FreeEnergyResult or None on error
    """
    try:
        # Approximate posterior q(z) parameterized by meta_score
        # Map meta_score (0-100) to μ_q and σ_q
        mu_q = (meta_score - 50.0) / 25.0  # center around 0, scale to ~[-2, 2]

        # σ_q derived from component variance (uncertainty in posterior)
        comp_vals = [v for v in component_breakdown.values() if isinstance(v, (int, float))]
        if comp_vals:
            comp_mean = sum(comp_vals) / len(comp_vals)
            comp_var = sum((v - comp_mean) ** 2 for v in comp_vals) / len(comp_vals)
            sigma_q = max(math.sqrt(comp_var) / 50.0, 0.1)  # scale to reasonable range
        else:
            sigma_q = 1.0

        # KL divergence: KL(N(μ,σ²) || N(0,1)) = ½(μ² + σ² - log(σ²) - 1)
        log_sigma_sq = math.log(max(sigma_q * sigma_q, 1e-10))
        kl = 0.5 * (mu_q * mu_q + sigma_q * sigma_q - log_sigma_sq - 1.0)
        kl = max(0.0, kl)  # KL is always non-negative

        # Reconstruction term: E_q[log p(x|z)] ≈ -MSE(predicted, actual)
        # omega_predicted from meta_score mapping
        omega_predicted = meta_score  # meta_score is P(unsafe) scaled 0-100
        mse = (omega_predicted - omega_actual) ** 2 / 10000.0  # normalize by 100²
        reconstruction = -mse  # log-likelihood proxy (negative MSE)

        # ELBO = reconstruction - KL
        elbo = reconstruction - kl

        # Free Energy F = -ELBO
        F = -elbo

        # Surprise normalization: F / max_observed_F
        if max_observed_F is not None and max_observed_F > 0:
            surprise = min(1.0, max(0.0, F / max_observed_F))
        else:
            # Fallback: F / 100.0
            surprise = min(1.0, max(0.0, F / 100.0))

        return FreeEnergyResult(
            F=round(F, 4),
            elbo=round(elbo, 4),
            kl_divergence=round(kl, 4),
            reconstruction=round(reconstruction, 4),
            surprise=round(surprise, 4),
        )
    except Exception:
        return None
