from dataclasses import dataclass
from typing import Literal
import math

@dataclass
class MemoryEntry:
    id: str
    content: str
    type: str
    timestamp_age_days: float
    source_trust: float        # 0.0 – 1.0
    source_conflict: float     # 0.0 – 1.0  (Dempster-Shafer K)
    downstream_count: int      # blast radius
    r_belief: float = 0.5      # 0.0 – 1.0  (model belief divergence)

@dataclass
class PreflightResult:
    omega_mem_final: float
    recommended_action: Literal["USE_MEMORY","WARN","ASK_USER","BLOCK"]
    assurance_score: float
    explainability_note: str
    component_breakdown: dict

# Default beta weights — v1.0
WEIGHTS = {
    "s_freshness":    0.15,
    "s_drift":        0.15,
    "s_provenance":   0.12,
    "s_propagation":  0.12,
    "r_recall":       0.18,
    "r_encode":       0.12,
    "s_interference": 0.10,
    "s_recovery":    -0.10,
    "r_belief":       0.05,
}

C_ACTION = {
    "informational": 1.0,
    "reversible":    1.3,
    "irreversible":  1.8,
    "destructive":   2.5,
}

C_DOMAIN = {
    "general":          1.0,
    "customer_support": 1.2,
    "coding":           1.3,
    "legal":            1.6,
    "fintech":          1.8,
    "medical":          2.0,
}

def compute(
    entries: list[MemoryEntry],
    action_type: str = "reversible",
    domain: str = "general",
) -> PreflightResult:

    if not entries:
        return PreflightResult(0, "USE_MEMORY", 100, "No memory entries.", {})

    # Component scores (0–100, higher = more risk)
    s_freshness   = min(100, sum(e.timestamp_age_days * 1.2 for e in entries) / len(entries))
    s_provenance  = min(100, sum((1 - e.source_trust) * 100 for e in entries) / len(entries))
    s_interference= min(100, sum(e.source_conflict * 100 for e in entries) / len(entries))
    s_propagation = min(100, sum(e.downstream_count * 8 for e in entries) / len(entries))
    r_recall      = min(100, s_freshness * 0.6 + s_provenance * 0.4)
    r_encode      = min(100, s_provenance * 0.5)
    s_drift       = min(100, s_freshness * 0.4 + s_interference * 0.6)
    s_recovery    = max(0, 100 - s_freshness * 0.5)

    # R_belief: inverse of model belief — low belief = high risk
    # r_belief 0.0–1.0 maps to risk 100–0 (inverted)
    r_belief_score = min(100, sum((1 - e.r_belief) * 100 for e in entries) / len(entries))

    components = {
        "s_freshness":    s_freshness,
        "s_drift":        s_drift,
        "s_provenance":   s_provenance,
        "s_propagation":  s_propagation,
        "r_recall":       r_recall,
        "r_encode":       r_encode,
        "s_interference": s_interference,
        "s_recovery":     s_recovery,
        "r_belief":       r_belief_score,
    }

    omega = sum(WEIGHTS[k] * v for k, v in components.items())
    omega = max(0, min(100, omega))

    c = C_ACTION.get(action_type, 1.0) * C_DOMAIN.get(domain, 1.0)
    omega_final = min(100, omega * c)

    # Decision
    if omega_final < 25:
        action = "USE_MEMORY"
    elif omega_final < 45:
        action = "WARN"
    elif omega_final < 70:
        action = "ASK_USER"
    else:
        action = "BLOCK"

    # Simple assurance score (inverse of risk)
    assurance = max(0, round(100 - omega_final * 0.7))

    # Explainability
    worst = max(components, key=components.get)
    note = f"Highest risk: {worst} ({components[worst]:.1f}/100). Action: {action}."

    # R_belief advisory: low belief suggests external storage
    avg_belief = sum(e.r_belief for e in entries) / len(entries)
    if avg_belief < 0.2:
        note += " Low model belief — consider saving to external memory."
    elif avg_belief < 0.4:
        note += " Weak model belief — verify with user before relying on this memory."

    return PreflightResult(
        omega_mem_final=round(omega_final, 1),
        recommended_action=action,
        assurance_score=assurance,
        explainability_note=note,
        component_breakdown={k: round(v, 1) for k, v in components.items()},
    )
