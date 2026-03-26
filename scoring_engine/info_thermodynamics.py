from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class InfoThermodynamicsResult:
    transfer_entropy: float       # T_{X→Y}: directional information flow
    max_flow: float               # max(T_{X→Y}, T_{Y→X})
    landauer_bound: float         # kT·ln(2)·bits_erased — minimum energy to erase memory
    information_temperature: float  # τ_info = Var(scores) / mean(scores)
    entropy_production: float     # σ = ΔS_system + ΔS_environment ≥ 0
    reversibility: float          # 0 (irreversible) → 1 (reversible)


def _transfer_entropy(source: list[float], target: list[float], lag: int = 1) -> float:
    """Transfer entropy T_{X→Y} = H(Y_t | Y_{t-1}) - H(Y_t | Y_{t-1}, X_{t-1}).

    Measures directional information flow from source → target.
    Uses binned estimation (4 bins) for efficiency.

    Returns T_{X→Y} in nats (≥ 0).
    """
    n = len(target) - lag
    if n < 3 or len(source) < n + lag:
        return 0.0

    # Bin values into 4 categories
    def _bin(val: float) -> int:
        if val <= 25:
            return 0
        if val <= 50:
            return 1
        if val <= 75:
            return 2
        return 3

    # Count joint and marginal frequencies
    # P(y_t, y_{t-1}, x_{t-1})
    joint_3 = {}  # (y_t_bin, y_prev_bin, x_prev_bin) → count
    joint_2_yx = {}  # (y_t_bin, y_prev_bin) → count
    joint_2_ypxp = {}  # (y_prev_bin, x_prev_bin) → count
    marginal_yp = {}  # y_prev_bin → count

    for t in range(lag, len(target)):
        if t - lag >= len(source):
            break
        yt = _bin(target[t])
        yp = _bin(target[t - lag])
        xp = _bin(source[t - lag])

        k3 = (yt, yp, xp)
        joint_3[k3] = joint_3.get(k3, 0) + 1

        k2yx = (yt, yp)
        joint_2_yx[k2yx] = joint_2_yx.get(k2yx, 0) + 1

        k2yxp = (yp, xp)
        joint_2_ypxp[k2yxp] = joint_2_ypxp.get(k2yxp, 0) + 1

        marginal_yp[yp] = marginal_yp.get(yp, 0) + 1

    total = sum(joint_3.values()) or 1

    # T_{X→Y} = Σ p(y_t, y_{t-1}, x_{t-1}) · log[p(y_t|y_{t-1},x_{t-1}) / p(y_t|y_{t-1})]
    te = 0.0
    eps = 1e-10
    for (yt, yp, xp), count in joint_3.items():
        p_joint = count / total
        p_yt_given_ypxp = count / max(joint_2_ypxp.get((yp, xp), 1), 1)
        p_yt_given_yp = joint_2_yx.get((yt, yp), 1) / max(marginal_yp.get(yp, 1), 1)

        if p_yt_given_ypxp > eps and p_yt_given_yp > eps:
            te += p_joint * math.log(p_yt_given_ypxp / p_yt_given_yp)

    return max(0.0, te)


def compute_info_thermodynamics(
    score_history: list[float],
    current_score: float,
    component_scores: list[float],
    healing_counter: int = 0,
    min_observations: int = 5,
) -> Optional[InfoThermodynamicsResult]:
    """Information Thermodynamics for memory state analysis.

    Computes:
    - Transfer entropy T_{X→Y}: directional information flow between
      score history (past) and current state
    - Landauer's bound: kT·ln(2)·bits — minimum energy cost of erasing memory
    - Information temperature: τ = Var/Mean of component scores
    - Entropy production: irreversibility measure σ ≥ 0
    - Reversibility: 1/(1 + σ), 0 = irreversible, 1 = reversible

    Args:
        score_history: past omega_mem_final scores
        current_score: current omega_mem_final
        component_scores: current component breakdown values
        healing_counter: number of heals applied (erasure events)
        min_observations: minimum history length (default 5)

    Returns:
        InfoThermodynamicsResult or None if insufficient data
    """
    if len(score_history) < min_observations:
        return None

    try:
        all_scores = score_history + [current_score]
        n = len(all_scores)

        # Transfer entropy: split history into two halves as source/target
        mid = n // 2
        source = all_scores[:mid + 1]
        target = all_scores[mid:]
        # Also compute reverse direction
        te_forward = _transfer_entropy(source, target)
        te_reverse = _transfer_entropy(target, source)
        max_flow = max(te_forward, te_reverse)

        # Landauer's bound: E_min = kT·ln(2)·bits_erased
        # In information units: bits erased ≈ healing_counter (each heal erases info)
        # kT·ln(2) ≈ 1 in normalized units
        bits_erased = max(healing_counter, 0)
        landauer = round(math.log(2) * bits_erased, 4)

        # Information temperature: τ_info = Var(scores) / Mean(scores)
        if component_scores:
            mean_c = sum(component_scores) / len(component_scores) if component_scores else 1.0
            var_c = sum((s - mean_c) ** 2 for s in component_scores) / max(len(component_scores), 1)
            info_temp = var_c / max(mean_c, 0.01)
        else:
            info_temp = 1.0

        # Entropy production: σ = |ΔS| where ΔS is change in score entropy
        # Approximate from score changes
        changes = [all_scores[i + 1] - all_scores[i] for i in range(n - 1)]
        abs_changes = [abs(c) for c in changes]
        mean_abs = sum(abs_changes) / max(len(abs_changes), 1)
        # σ ≈ mean absolute change / 100 (normalized)
        entropy_production = round(mean_abs / 100.0, 4)

        # Reversibility: 1 / (1 + σ)
        reversibility = round(1.0 / (1.0 + entropy_production * 10), 4)

        return InfoThermodynamicsResult(
            transfer_entropy=round(te_forward, 4),
            max_flow=round(max_flow, 4),
            landauer_bound=landauer,
            information_temperature=round(info_temp, 4),
            entropy_production=entropy_production,
            reversibility=reversibility,
        )
    except Exception:
        return None
