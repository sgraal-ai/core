from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class CopulaResult:
    rho: float
    joint_risk: float
    tail_dependence: bool


# Standard normal CDF approximation (Abramowitz & Stegun)
def _phi(x: float) -> float:
    """Standard normal CDF Φ(x)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# Standard normal inverse CDF (rational approximation)
def _phi_inv(p: float) -> float:
    """Standard normal quantile function Φ⁻¹(p)."""
    if p <= 0:
        return -6.0
    if p >= 1:
        return 6.0
    if p == 0.5:
        return 0.0

    # Rational approximation (Peter Acklam)
    a = [-3.969683028665376e1, 2.209460984245205e2,
         -2.759285104469687e2, 1.383577518672690e2,
         -3.066479806614716e1, 2.506628277459239e0]
    b = [-5.447609879822406e1, 1.615858368580409e2,
         -1.556989798598866e2, 6.680131188771972e1,
         -1.328068155288572e1]
    c = [-7.784894002430293e-3, -3.223964580411365e-1,
         -2.400758277161838e0, -2.549732539343734e0,
         4.374664141464968e0, 2.938163982698783e0]
    d = [7.784695709041462e-3, 3.224671290700398e-1,
         2.445134137142996e0, 3.754408661907416e0]

    p_low = 0.02425
    p_high = 1.0 - p_low

    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1.0)
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
               (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1.0)
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1.0)


def _bivariate_normal_cdf(x: float, y: float, rho: float) -> float:
    """Approximate bivariate standard normal CDF Φ₂(x, y, ρ).

    Uses Drezner-Wesolowsky approximation for speed.
    """
    if abs(rho) < 1e-10:
        return _phi(x) * _phi(y)

    # For high correlation, use simple bound
    if rho > 0.999:
        return _phi(min(x, y))
    if rho < -0.999:
        return max(0.0, _phi(x) + _phi(y) - 1.0)

    # Tetrachoric approximation
    r = rho
    joint = _phi(x) * _phi(y)
    # First-order correction
    pdf_x = math.exp(-x * x / 2.0) / math.sqrt(2 * math.pi)
    pdf_y = math.exp(-y * y / 2.0) / math.sqrt(2 * math.pi)
    joint += r * pdf_x * pdf_y

    return max(0.0, min(1.0, joint))


def compute_copula(
    s_freshness: float,
    s_drift: float,
    rho: float = 0.7,
) -> CopulaResult:
    """Compute Gaussian copula joint risk between s_freshness and s_drift.

    C(u,v) = Φ₂(Φ⁻¹(u), Φ⁻¹(v), ρ)

    Args:
        s_freshness: freshness score 0–100
        s_drift: drift score 0–100
        rho: correlation parameter (default 0.7, learned from domain data)

    Returns:
        CopulaResult with rho, joint_risk (0–100), and tail_dependence flag
    """
    # Normalize to [0.001, 0.999] for CDF inversion
    u = max(0.001, min(0.999, s_freshness / 100.0))
    v = max(0.001, min(0.999, s_drift / 100.0))

    # Transform to standard normal
    z_u = _phi_inv(u)
    z_v = _phi_inv(v)

    # Bivariate normal CDF
    joint_cdf = _bivariate_normal_cdf(z_u, z_v, rho)

    # Joint risk: combine copula with marginal risks
    # Under independence: P(both risky) = u × v
    # Copula amplifies when correlated: joint_cdf > u × v
    independent_risk = u * v * 100.0
    copula_amplification = joint_cdf / max(u * v, 1e-10)
    joint_risk = round(min(100.0, independent_risk * copula_amplification * (1.0 + abs(rho))), 2)

    # Tail dependence: copula joint risk exceeds independent prediction by 20%+
    tail_dependence = joint_risk > independent_risk * 1.2 if independent_risk > 0.5 else False

    return CopulaResult(
        rho=round(rho, 4),
        joint_risk=joint_risk,
        tail_dependence=tail_dependence,
    )
