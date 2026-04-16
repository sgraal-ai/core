"""Offline/edge mode for the Sgraal Python SDK.

Pure Python, zero dependencies (stdlib only). Implements the 5-signal fast path
so Sgraal preflight can run on Raspberry Pis, medical devices, air-gapped
networks, and any environment that cannot reach api.sgraal.com.

Signals:
    Risk       (freshness)    — Weibull-style decay per memory type
    Decay      (drift)        — source_conflict * 100
    Trust      (provenance)   — (1 - source_trust) * 100
    Corruption (interference) — mean source_conflict across entries
    Belief     (conviction)   — low-trust penalty

The single public function is :func:`edge_preflight`.
"""

from __future__ import annotations

import math
from typing import Any

SDK_VERSION = "0.3.1"

# Weights must sum to 1.0
_WEIGHTS = {
    "risk": 0.30,
    "decay": 0.20,
    "trust": 0.25,
    "corruption": 0.15,
    "belief": 0.10,
}

# Weibull-style decay lambdas per memory type
_LAMBDA_BY_TYPE = {
    "tool_state": 0.15,
    "episodic": 0.05,
    "semantic": 0.02,
    "identity": 0.002,
    "shared_workflow": 0.08,
    "preference": 0.03,
    "policy": 0.005,
}

# Default lambda for unknown types
_DEFAULT_LAMBDA = 0.05

# Per-type thresholds (strict types BLOCK earlier)
PER_TYPE_THRESHOLDS = {
    "identity": 13,
    "policy": 17,
    "semantic": 21,
    "preference": 33,
    "episodic": 37,
    "shared_workflow": 43,
    "tool_state": 47,
}

# Global decision thresholds
_WARN_THRESHOLD = 25
_ASK_USER_THRESHOLD = 45
_BLOCK_THRESHOLD = 70

# Action types that tighten BLOCK by this many points
_HIGH_STAKES_ACTIONS = {"destructive", "irreversible"}
_HIGH_STAKES_BLOCK_ADJUSTMENT = 10


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp a float into [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Coerce to float, returning default on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _entry_signals(entry: dict) -> dict:
    """Compute the 5 raw signal scores (0-100) for a single entry."""
    mem_type = entry.get("type", "")
    lam = _LAMBDA_BY_TYPE.get(mem_type, _DEFAULT_LAMBDA)

    age = max(0.0, _safe_float(entry.get("timestamp_age_days", 0.0)))
    trust = _safe_float(entry.get("source_trust", 0.5))
    # Clamp trust into [0, 1]
    if trust < 0.0:
        trust = 0.0
    elif trust > 1.0:
        trust = 1.0

    conflict = _safe_float(entry.get("source_conflict", 0.0))
    if conflict < 0.0:
        conflict = 0.0
    elif conflict > 1.0:
        conflict = 1.0

    # Risk (freshness): Weibull-style 1 - exp(-lambda * age)
    risk = (1.0 - math.exp(-lam * age)) * 100.0

    # Decay (drift): straight from source_conflict
    decay = conflict * 100.0

    # Trust (provenance): inverse of source_trust
    trust_signal = (1.0 - trust) * 100.0

    # Corruption (interference): single-entry proxy = conflict
    corruption = conflict * 100.0

    # Belief (conviction)
    if trust < 0.3:
        belief = 80.0
    else:
        belief = max(0.0, (0.5 - trust) * 100.0)

    return {
        "risk": _clamp(risk),
        "decay": _clamp(decay),
        "trust": _clamp(trust_signal),
        "corruption": _clamp(corruption),
        "belief": _clamp(belief),
        "_type": mem_type,
    }


def _aggregate_signals(per_entry: list) -> dict:
    """Aggregate per-entry signals.

    Averages Risk/Decay/Corruption across entries; takes worst-case
    (maximum) for Trust and Belief since provenance/conviction failures
    on any single entry can poison the whole state.
    """
    n = len(per_entry)
    risk = sum(s["risk"] for s in per_entry) / n
    decay = sum(s["decay"] for s in per_entry) / n
    corruption = sum(s["corruption"] for s in per_entry) / n
    trust = max(s["trust"] for s in per_entry)
    belief = max(s["belief"] for s in per_entry)

    return {
        "risk": risk,
        "decay": decay,
        "trust": trust,
        "corruption": corruption,
        "belief": belief,
    }


def _compute_omega(signals: dict) -> float:
    """Weighted average of the 5 signals, clamped to [0, 100]."""
    omega = (
        _WEIGHTS["risk"] * signals["risk"]
        + _WEIGHTS["decay"] * signals["decay"]
        + _WEIGHTS["trust"] * signals["trust"]
        + _WEIGHTS["corruption"] * signals["corruption"]
        + _WEIGHTS["belief"] * signals["belief"]
    )
    return _clamp(omega)


def _dominant_entry(per_entry: list) -> dict:
    """Entry whose Risk signal contributes most to the aggregate."""
    return max(per_entry, key=lambda s: s["risk"])


def _explain(signals: dict, dominant_type: str, omega: float) -> str:
    """One-line human-readable rationale focused on the top signal."""
    if not signals:
        return "No memory state provided"

    ranked = sorted(
        (
            ("risk", signals["risk"], "Stale"),
            ("decay", signals["decay"], "Drifting"),
            ("trust", signals["trust"], "Low-trust"),
            ("corruption", signals["corruption"], "Conflicted"),
            ("belief", signals["belief"], "Low-conviction"),
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    top_name, top_value, top_label = ranked[0]

    type_label = dominant_type or "memory"
    if top_value < 10.0:
        return f"Healthy {type_label} (omega={omega:.1f})"
    return f"{top_label} {type_label} (primary {top_name}={top_value:.1f})"


def _decide(
    omega: float,
    dominant_type: str,
    action_type: str,
) -> tuple:
    """Map omega + type + action to a decision.

    Returns (decision, per_type_applied: bool, effective_block: float).
    """
    global_block = float(_BLOCK_THRESHOLD)
    if action_type in _HIGH_STAKES_ACTIONS:
        global_block -= _HIGH_STAKES_BLOCK_ADJUSTMENT

    per_type = PER_TYPE_THRESHOLDS.get(dominant_type)
    if per_type is not None:
        # Tighten further for high-stakes actions, never below 5
        effective_per_type = per_type
        if action_type in _HIGH_STAKES_ACTIONS:
            effective_per_type = max(5.0, per_type - _HIGH_STAKES_BLOCK_ADJUSTMENT)
        # Per-type BLOCK dominates when it fires
        if omega >= effective_per_type:
            return "BLOCK", True, float(effective_per_type)

    # Fall back to global thresholds
    if omega >= global_block:
        decision = "BLOCK"
    elif omega >= _ASK_USER_THRESHOLD:
        decision = "ASK_USER"
    elif omega >= _WARN_THRESHOLD:
        decision = "WARN"
    else:
        decision = "USE_MEMORY"

    return decision, per_type is not None, global_block


def edge_preflight(
    memory_state: list,
    domain: str = "general",
    action_type: str = "standard",
) -> dict:
    """Offline 5-signal preflight.

    Args:
        memory_state: List of memory entries. Each entry should include
            ``type``, ``timestamp_age_days``, ``source_trust``, and
            ``source_conflict``. Missing fields fall back to safe defaults.
        domain: Domain label (informational only in edge mode).
        action_type: ``standard``, ``informational``, ``reversible``,
            ``irreversible``, or ``destructive``. ``destructive`` and
            ``irreversible`` tighten the BLOCK threshold by 10 points.

    Returns:
        Dict with keys ``omega``, ``decision``, ``explanation``,
        ``five_signals``, ``per_type_threshold_applied``,
        ``dominant_type``, ``edge_mode``, ``sdk_version``,
        ``domain``, ``action_type``, ``effective_block_threshold``,
        and ``n_entries``.
    """
    if not isinstance(memory_state, list) or len(memory_state) == 0:
        return {
            "omega": 0.0,
            "decision": "USE_MEMORY",
            "explanation": "No memory state provided; nothing to score",
            "five_signals": {
                "risk": 0.0,
                "decay": 0.0,
                "trust": 0.0,
                "corruption": 0.0,
                "belief": 0.0,
            },
            "per_type_threshold_applied": False,
            "dominant_type": "",
            "edge_mode": True,
            "sdk_version": SDK_VERSION,
            "domain": domain,
            "action_type": action_type,
            "effective_block_threshold": float(_BLOCK_THRESHOLD),
            "n_entries": 0,
        }

    per_entry = [_entry_signals(e if isinstance(e, dict) else {}) for e in memory_state]
    aggregate = _aggregate_signals(per_entry)
    omega = _compute_omega(aggregate)
    dominant = _dominant_entry(per_entry)
    dominant_type = dominant["_type"]
    decision, per_type_applied, effective_block = _decide(
        omega, dominant_type, action_type
    )
    explanation = _explain(aggregate, dominant_type, omega)

    return {
        "omega": round(omega, 2),
        "decision": decision,
        "explanation": explanation,
        "five_signals": {
            "risk": round(aggregate["risk"], 2),
            "decay": round(aggregate["decay"], 2),
            "trust": round(aggregate["trust"], 2),
            "corruption": round(aggregate["corruption"], 2),
            "belief": round(aggregate["belief"], 2),
        },
        "per_type_threshold_applied": per_type_applied,
        "dominant_type": dominant_type,
        "edge_mode": True,
        "sdk_version": SDK_VERSION,
        "domain": domain,
        "action_type": action_type,
        "effective_block_threshold": float(effective_block),
        "n_entries": len(memory_state),
    }
