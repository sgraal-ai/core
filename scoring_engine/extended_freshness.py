from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class EntryFreshness:
    entry_id: str
    score: float
    trend: Optional[float] = None
    half_life: Optional[float] = None


@dataclass
class ExtendedFreshnessResult:
    gompertz: list[EntryFreshness]
    holt_winters: Optional[list[EntryFreshness]]
    power_law: list[EntryFreshness]
    recommended_model: str
    ensemble_freshness: float
    models_used: list[str]


def _gompertz(t: float, theta: float = 0.1, alpha: float = 0.05) -> float:
    """Gompertz decay: S = exp(-θ · exp(α · t)). Slow then rapid decline."""
    return math.exp(-theta * math.exp(alpha * t))


def _power_law(t: float, tau: float = 10.0, alpha: float = 0.5) -> float:
    """Power-law decay: S = (1 + t/τ)^(-α). Long-tail, never fully expires."""
    return (1.0 + t / tau) ** (-alpha)


def _power_law_half_life(tau: float = 10.0, alpha: float = 0.5) -> float:
    """Half-life for power-law: t where S = 0.5 → t = τ · (2^(1/α) - 1)."""
    return tau * (2.0 ** (1.0 / alpha) - 1.0)


def _holt_winters(
    history: list[float],
    current: float,
    alpha: float = 0.3,
    beta: float = 0.1,
) -> tuple[float, float]:
    """Holt-Winters double exponential smoothing.

    Level: ŷ(t) = α·y(t) + (1-α)·(ŷ(t-1) + b(t-1))
    Trend: b(t) = β·(ŷ(t) - ŷ(t-1)) + (1-β)·b(t-1)

    Returns (forecast, trend).
    """
    if not history:
        return current, 0.0

    # Initialize
    level = history[0]
    trend = (history[1] - history[0]) if len(history) > 1 else 0.0

    for y in history[1:]:
        prev_level = level
        level = alpha * y + (1 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend

    # One more step with current
    prev_level = level
    level = alpha * current + (1 - alpha) * (level + trend)
    trend = beta * (level - prev_level) + (1 - beta) * trend

    # Forecast = level + trend (next step)
    forecast = level + trend

    # Convert to freshness score (0-1): higher forecast = more degraded = lower freshness
    freshness = max(0.0, min(1.0, 1.0 - forecast / 100.0))

    return freshness, trend


def _recommend_model(entry_type: str) -> str:
    """Recommend freshness model based on memory type."""
    t = entry_type.lower() if entry_type else ""
    if "preference" in t or "user" in t:
        return "gompertz"
    if "factual" in t or "research" in t or "semantic" in t:
        return "power_law"
    if "tool_state" in t or "shared_workflow" in t:
        return "weibull"
    return "weibull"


def compute_extended_freshness(
    entries: list[dict],
    history: Optional[list[float]] = None,
) -> Optional[ExtendedFreshnessResult]:
    """Extended freshness models: Gompertz, Holt-Winters, Power-law.

    Args:
        entries: list of dicts with id, type, timestamp_age_days
        history: optional omega score history for Holt-Winters

    Returns:
        ExtendedFreshnessResult or None if no entries
    """
    if not entries:
        return None

    try:
        gompertz_results = []
        power_law_results = []
        holt_winters_results = None

        for e in entries:
            eid = e.get("id", "unknown")
            age = e.get("timestamp_age_days", 0)

            # Gompertz
            g_score = round(_gompertz(age), 4)
            gompertz_results.append(EntryFreshness(entry_id=eid, score=g_score))

            # Power-law
            pl_score = round(_power_law(age), 4)
            pl_hl = round(_power_law_half_life(), 2)
            power_law_results.append(EntryFreshness(entry_id=eid, score=pl_score, half_life=pl_hl))

        # Holt-Winters: only if we have enough history
        hw_available = False
        if history and len(history) >= 5:
            holt_winters_results = []
            hw_available = True
            for e in entries:
                eid = e.get("id", "unknown")
                age = e.get("timestamp_age_days", 0)
                hw_fresh, hw_trend = _holt_winters(history, age)
                holt_winters_results.append(EntryFreshness(
                    entry_id=eid, score=round(hw_fresh, 4), trend=round(hw_trend, 4),
                ))

        # Recommended model based on first entry type
        first_type = entries[0].get("type", "") if entries else ""
        recommended = _recommend_model(first_type)

        # Ensemble freshness with weight redistribution
        base_weights = {"weibull": 0.4, "gompertz": 0.2, "holt_winters": 0.2, "power_law": 0.2}
        models_used = ["weibull", "gompertz", "power_law"]

        if not hw_available:
            # Redistribute holt_winters weight
            hw_weight = base_weights.pop("holt_winters")
            remaining = list(base_weights.keys())
            share = hw_weight / len(remaining)
            for k in remaining:
                base_weights[k] += share
        else:
            models_used.append("holt_winters")

        # Compute per-model average freshness
        weibull_avg = sum(math.exp(-e.get("timestamp_age_days", 0) / 100.0) for e in entries) / max(len(entries), 1)
        gompertz_avg = sum(g.score for g in gompertz_results) / max(len(gompertz_results), 1)
        power_law_avg = sum(p.score for p in power_law_results) / max(len(power_law_results), 1)

        ensemble = base_weights.get("weibull", 0) * weibull_avg
        ensemble += base_weights.get("gompertz", 0) * gompertz_avg
        ensemble += base_weights.get("power_law", 0) * power_law_avg

        if hw_available and holt_winters_results:
            hw_avg = sum(h.score for h in holt_winters_results) / max(len(holt_winters_results), 1)
            ensemble += base_weights.get("holt_winters", 0) * hw_avg

        ensemble_freshness = round(max(0.0, min(1.0, ensemble)), 4)

        return ExtendedFreshnessResult(
            gompertz=gompertz_results,
            holt_winters=holt_winters_results,
            power_law=power_law_results,
            recommended_model=recommended,
            ensemble_freshness=ensemble_freshness,
            models_used=models_used,
        )
    except Exception:
        return None
