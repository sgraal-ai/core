from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class CohomologicalGradientResult:
    gradient_norm: float
    h1_contribution: float
    fim_contribution: float
    cohomological_update_used: bool


def compute_cohomological_gradient(
    free_energy_F: float = 0.0,
    h1_rank: int = 0,
    fisher_rao_diagonal: Optional[list[float]] = None,
    lambda_weights: Optional[list[float]] = None,
) -> Optional[CohomologicalGradientResult]:
    """Cohomological Learning Gradient.

    cohomological_gradient_i = (dL_FE/dlambda_i + h1_rank) / (g_ii + eps)

    Uses Fisher-Rao diagonal FIM and sheaf H1 rank.

    Args:
        free_energy_F: free energy F value
        h1_rank: sheaf cohomology H1 rank
        fisher_rao_diagonal: Fisher-Rao metric diagonal [g_ii]
        lambda_weights: L_v4 lambda weights for gradient approximation

    Returns:
        CohomologicalGradientResult or None on error
    """
    try:
        eps = 1e-8

        if fisher_rao_diagonal and lambda_weights:
            # Full cohomological gradient
            n = min(len(fisher_rao_diagonal), len(lambda_weights))
            gradients = []
            for i in range(n):
                # Approximate dL_FE/dlambda_i as F * lambda_i (linear proxy)
                dl = free_energy_F * lambda_weights[i]
                g_ii = fisher_rao_diagonal[i] if i < len(fisher_rao_diagonal) else 1.0
                grad_i = (dl + h1_rank) / (g_ii + eps)
                gradients.append(grad_i)

            gradient_norm = math.sqrt(sum(g * g for g in gradients))
            h1_contrib = round(h1_rank / max(sum(fisher_rao_diagonal) / len(fisher_rao_diagonal) + eps, eps), 4)
            fim_contrib = round(sum(1.0 / (g + eps) for g in fisher_rao_diagonal) / len(fisher_rao_diagonal), 4)
            used = True
        else:
            # Fallback: simplified gradient without FIM
            gradient_norm = abs(free_energy_F) + h1_rank
            h1_contrib = float(h1_rank)
            fim_contrib = 0.0
            used = False

        return CohomologicalGradientResult(
            gradient_norm=round(gradient_norm, 4),
            h1_contribution=h1_contrib,
            fim_contribution=fim_contrib,
            cohomological_update_used=used,
        )
    except Exception:
        return None
