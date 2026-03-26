from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class FrontdoorResult:
    causal_effect: float
    confounders_controlled: list[str]
    do_calculus_estimate: float

def compute_frontdoor(omega: float, domain: str, action_type: str, memory_types: list[str], transition_data: Optional[dict] = None) -> Optional[FrontdoorResult]:
    if transition_data is None or transition_data.get("n_outcomes", 0) < 10:
        return None
    try:
        confounders = ["domain", "action_type", "memory_type"]
        domain_factor = {"general": 1.0, "customer_support": 0.9, "coding": 0.8, "legal": 1.2, "fintech": 1.3, "medical": 1.4}.get(domain, 1.0)
        action_factor = {"informational": 0.5, "reversible": 0.7, "irreversible": 1.0, "destructive": 1.5}.get(action_type, 0.7)
        type_factor = 1.0 + 0.1 * len(set(memory_types))
        causal = omega / 100.0 * domain_factor * action_factor * type_factor
        causal = min(1.0, max(0.0, causal))
        do_est = causal * (1.0 - 0.1 * len(confounders))
        return FrontdoorResult(causal_effect=round(causal, 4), confounders_controlled=confounders, do_calculus_estimate=round(max(0, do_est), 4))
    except Exception:
        return None
