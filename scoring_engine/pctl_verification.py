from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import Optional

STATES = ["SAFE","WARN","DEGRADED","CRITICAL"]
TRANSITIONS = [[0.7,0.2,0.08,0.02],[0.2,0.5,0.25,0.05],[0.05,0.15,0.5,0.3],[0.01,0.04,0.15,0.8]]
HEAL_TRANS = [[0.9,0.08,0.01,0.01],[0.6,0.3,0.08,0.02],[0.4,0.35,0.2,0.05],[0.3,0.3,0.25,0.15]]

@dataclass
class PCTLResult:
    p_ef_recovery: float
    p_ag_heal_works: float
    p_eg_stable: float
    simulations: int

def _state_idx(omega: float) -> int:
    if omega<=25: return 0
    if omega<=50: return 1
    if omega<=75: return 2
    return 3

def _sim_next(state: int, trans: list, seed: str, step: int) -> int:
    h = int(hashlib.sha256(f"{seed}:{step}".encode()).hexdigest()[:8], 16)
    u = (h % 10000) / 10000.0
    cum = 0.0
    for j in range(4):
        cum += trans[state][j]
        if u < cum: return j
    return 3

def compute_pctl(omega: float, n_sims: int = 100, steps: int = 10, seed: str = None) -> Optional[PCTLResult]:
    try:
        s0 = _state_idx(omega)
        ef_count, ag_count, eg_count = 0, 0, 0
        _base_seed = seed or f"pctl:{omega}"
        for sim in range(n_sims):
            seed = f"{_base_seed}:{sim}"
            # EF: reaches SAFE or WARN
            s = s0; ef_ok = s <= 1
            for t in range(steps):
                s = _sim_next(s, TRANSITIONS, seed+"ef", t)
                if s <= 1: ef_ok = True; break
            if ef_ok: ef_count += 1
            # AG: heal always improves
            s = s0; ag_ok = True
            for t in range(steps):
                sh = _sim_next(s, HEAL_TRANS, seed+"ag", t)
                if s > 0 and sh >= s: ag_ok = False; break
                s = _sim_next(s, TRANSITIONS, seed+"ags", t)
            if ag_ok: ag_count += 1
            # EG: stays below CRITICAL
            s = s0; eg_ok = s < 3
            for t in range(steps):
                s = _sim_next(s, TRANSITIONS, seed+"eg", t)
                if s >= 3: eg_ok = False; break
            if eg_ok: eg_count += 1
        return PCTLResult(p_ef_recovery=round(ef_count/n_sims,4), p_ag_heal_works=round(ag_count/n_sims,4), p_eg_stable=round(eg_count/n_sims,4), simulations=n_sims)
    except Exception: return None
