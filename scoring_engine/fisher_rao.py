from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class FIMInteraction:
    param_i: str
    param_j: str
    interaction: float


@dataclass
class FIMExtendedResult:
    top_interactions: list[FIMInteraction]
    most_sensitive: str


@dataclass
class FisherRaoResult:
    metric_diagonal: list[float]
    condition_number: float
    geometry: str  # "flat", "moderate", "curved"


def compute_fisher_rao(
    component_breakdown: dict[str, float],
    history: Optional[list[dict[str, float]]] = None,
) -> Optional[FisherRaoResult]:
    """Fisher-Rao metric diagonal approximation.

    g_ii = 1 / (Var(component_i) + ε)

    Args:
        component_breakdown: current component scores
        history: optional list of past component breakdowns for variance estimation

    Returns:
        FisherRaoResult or None on error
    """
    if not component_breakdown:
        return None

    try:
        eps = 1e-8
        keys = sorted(component_breakdown.keys())
        n = len(keys)

        if history and len(history) >= 2:
            # Compute variance from history
            diag = []
            for k in keys:
                vals = [h.get(k, 0.0) for h in history] + [component_breakdown[k]]
                m = sum(vals) / len(vals)
                var = sum((v - m) ** 2 for v in vals) / len(vals)
                diag.append(round(1.0 / (var + eps), 4))
        else:
            # Single-sample: use score magnitude as variance proxy
            vals = [component_breakdown[k] for k in keys]
            mean_v = sum(vals) / max(len(vals), 1)
            diag = []
            for k in keys:
                v = component_breakdown[k]
                var_proxy = (v - mean_v) ** 2
                diag.append(round(1.0 / (var_proxy + eps), 4))

        # Condition number: max(g) / min(g)
        max_g = max(diag) if diag else 1.0
        min_g = min(diag) if diag else 1.0
        cond = max_g / max(min_g, eps)

        if cond < 10:
            geometry = "flat"
        elif cond > 100:
            geometry = "curved"
        else:
            geometry = "moderate"

        return FisherRaoResult(
            metric_diagonal=diag,
            condition_number=round(cond, 4),
            geometry=geometry,
        )
    except Exception:
        return None


def compute_fim_extended(
    component_breakdown: dict[str, float],
) -> Optional[FIMExtendedResult]:
    """Extended FIM with off-diagonal top-3 interactions.

    Interaction(i,j) = |component_i * component_j| / (variance_proxy + eps)
    """
    if not component_breakdown or len(component_breakdown) < 2:
        return None

    try:
        eps = 1e-8
        keys = sorted(component_breakdown.keys())
        n = len(keys)
        vals = [component_breakdown[k] for k in keys]
        mean_v = sum(vals) / n

        interactions = []
        for i in range(n):
            for j in range(i + 1, n):
                vi = component_breakdown[keys[i]]
                vj = component_breakdown[keys[j]]
                var_proxy = ((vi - mean_v) ** 2 + (vj - mean_v) ** 2) / 2 + eps
                inter = abs(vi * vj) / var_proxy
                interactions.append(FIMInteraction(param_i=keys[i], param_j=keys[j], interaction=round(inter, 4)))

        interactions.sort(key=lambda x: x.interaction, reverse=True)
        top3 = interactions[:3]

        # Most sensitive: component with highest diagonal (largest variance contribution)
        max_idx = max(range(n), key=lambda i: abs(vals[i] - mean_v))
        most_sensitive = keys[max_idx]

        return FIMExtendedResult(top_interactions=top3, most_sensitive=most_sensitive)
    except Exception:
        return None
