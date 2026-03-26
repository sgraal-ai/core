from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class HomologyTorsionResult:
    torsion_detected: bool
    hallucination_risk: str
    torsion_evidence: str

def compute_homology_torsion(betti_1_max: int = 0, h1_rank: int = 0) -> HomologyTorsionResult:
    has_loops = betti_1_max > 0
    has_inconsistency = h1_rank > 0
    torsion = has_loops and has_inconsistency
    if torsion:
        risk = "high"
        evidence = f"beta_1={betti_1_max} AND h1_rank={h1_rank} — circular dependencies with inconsistent sections"
    elif has_loops or has_inconsistency:
        risk = "low"
        evidence = f"beta_1={betti_1_max}, h1_rank={h1_rank} — partial concern"
    else:
        risk = "none"
        evidence = "no torsion indicators"
    return HomologyTorsionResult(torsion_detected=torsion, hallucination_risk=risk, torsion_evidence=evidence)
