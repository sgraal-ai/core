from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class MutualInformationResult:
    mi_score: float
    nmi_score: float
    encoding_efficiency: str  # "high", "medium", "low"
    information_loss: float   # 1.0 - nmi_score


def _pearson_correlation(x: list[float], y: list[float]) -> float:
    """Pearson correlation coefficient ρ(X, Y)."""
    n = len(x)
    if n < 2:
        return 0.0

    mx = sum(x) / n
    my = sum(y) / n

    var_x = sum((xi - mx) ** 2 for xi in x) / n
    var_y = sum((yi - my) ** 2 for yi in y) / n

    if var_x < 1e-12 or var_y < 1e-12:
        return 0.0  # zero variance

    cov = sum((x[i] - mx) * (y[i] - my) for i in range(n)) / n
    rho = cov / (math.sqrt(var_x) * math.sqrt(var_y))

    # Clip to prevent log(0)
    return max(-0.999, min(0.999, rho))


def _shannon_entropy(values: list[float]) -> float:
    """H(X) = -Σ pᵢ · log(pᵢ) over normalized values."""
    total = sum(abs(v) for v in values) or 1.0
    probs = [abs(v) / total for v in values if abs(v) > 1e-10]
    if not probs:
        return 0.0
    return -sum(p * math.log(p + 1e-10) for p in probs)


def compute_mutual_information(
    entries: list[dict],
    component_keys: Optional[list[str]] = None,
) -> Optional[MutualInformationResult]:
    """Mutual Information and NMI for encoding efficiency measurement.

    MI(X;Y) ≈ -0.5 · log(1 - ρ²)
    NMI(X,Y) = MI(X,Y) / sqrt(H(X)·H(Y))

    X = input memory content proxy (source_trust, age, conflict)
    Y = stored component scores (from scoring engine output)

    Args:
        entries: list of dicts with source_trust, timestamp_age_days, etc.
        component_keys: optional list of component keys to use

    Returns:
        MutualInformationResult or None if < 2 entries
    """
    if len(entries) < 2:
        return None

    try:
        # X: input content proxy — source_trust values
        x = [e.get("source_trust", 0.5) for e in entries]

        # Y: stored representation proxy — derived score
        # Use a composite: trust * (1 - conflict) * age_decay
        y = []
        for e in entries:
            trust = e.get("source_trust", 0.5)
            conflict = e.get("source_conflict", 0.1) if e.get("source_conflict") is not None else 0.1
            age = e.get("timestamp_age_days", 0)
            age_decay = math.exp(-age / 100.0)
            y.append(trust * (1.0 - conflict) * age_decay)

        # Pearson correlation (clipped)
        rho = _pearson_correlation(x, y)

        # MI ≈ -0.5 · log(1 - ρ²)
        rho_sq = rho * rho
        mi = -0.5 * math.log(1.0 - rho_sq)
        mi = max(0.0, mi)

        # Shannon entropies for NMI
        h_x = _shannon_entropy(x)
        h_y = _shannon_entropy(y)

        # NMI = MI / sqrt(H(X) · H(Y))
        denom = math.sqrt(h_x * h_y) if h_x > 0 and h_y > 0 else 0.0
        if denom > 1e-10:
            nmi = min(1.0, mi / denom)
        else:
            nmi = 0.0

        # Classification
        if nmi > 0.7:
            efficiency = "high"
        elif nmi >= 0.4:
            efficiency = "medium"
        else:
            efficiency = "low"

        info_loss = round(1.0 - nmi, 4)

        return MutualInformationResult(
            mi_score=round(mi, 4),
            nmi_score=round(nmi, 4),
            encoding_efficiency=efficiency,
            information_loss=info_loss,
        )
    except Exception:
        return None
