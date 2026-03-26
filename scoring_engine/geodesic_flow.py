from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class GeodesicFlowResult:
    flow_magnitude: float
    parameter_velocity: list[float]
    manifold_distance: float


def compute_geodesic_flow(
    lambda_weights: list[float],
    loss_components: list[float],
    metric_diagonal: Optional[list[float]] = None,
    lr: float = 0.01,
) -> Optional[GeodesicFlowResult]:
    """Geodesic flow discrete approximation on parameter manifold.

    theta_{t+1} = theta_t - lr * g(theta)^-1 * grad_L
    manifold_distance = sqrt(sum_i g_ii * (delta_theta_i)^2)

    Args:
        lambda_weights: current L_v4 weights [11]
        loss_components: current loss values [11]
        metric_diagonal: Fisher-Rao metric diagonal (None = use lambda^2)
        lr: learning rate (default 0.01)

    Returns:
        GeodesicFlowResult or None on error
    """
    n = len(lambda_weights)
    if n == 0 or len(loss_components) != n:
        return None

    try:
        signs = [1, 1, 1, 1, 1, 1, 1, -1, 1, 1, 1]
        if len(signs) < n:
            signs.extend([1] * (n - len(signs)))

        velocity = []
        for i in range(n):
            grad = signs[i] * loss_components[i] if i < len(signs) else loss_components[i]

            if metric_diagonal and i < len(metric_diagonal):
                inv_g = 1.0 / max(metric_diagonal[i], 1e-8)
            else:
                inv_g = 1.0 / max(lambda_weights[i] ** 2, 1e-8)

            v = -lr * inv_g * grad
            velocity.append(round(v, 6))

        # Flow magnitude: ||velocity||
        flow_mag = math.sqrt(sum(v * v for v in velocity))

        # Manifold distance: sqrt(sum g_ii * delta_theta_i^2)
        m_dist = 0.0
        for i in range(n):
            if metric_diagonal and i < len(metric_diagonal):
                g_ii = metric_diagonal[i]
            else:
                g_ii = lambda_weights[i] ** 2
            m_dist += g_ii * velocity[i] ** 2
        m_dist = math.sqrt(max(0, m_dist))

        return GeodesicFlowResult(
            flow_magnitude=round(flow_mag, 6),
            parameter_velocity=velocity,
            manifold_distance=round(m_dist, 6),
        )
    except Exception:
        return None
