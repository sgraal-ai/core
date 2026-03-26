from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

SENSITIVE_TYPES = {"personal_data", "pii", "confidential"}

@dataclass
class SecurityTEResult:
    leakage_detected: bool
    leakage_paths: list[tuple[str, str]]
    risk_level: str

def compute_security_te(entries: list[dict], te_value: float = 0.0) -> Optional[SecurityTEResult]:
    if not entries: return None
    try:
        sensitive = [e for e in entries if e.get("type","").lower() in SENSITIVE_TYPES]
        non_sensitive = [e for e in entries if e.get("type","").lower() not in SENSITIVE_TYPES]
        paths = []
        if sensitive and non_sensitive and te_value > 0.05:
            for s in sensitive:
                for ns in non_sensitive:
                    paths.append((s.get("id","?"), ns.get("id","?")))
        leakage = len(paths) > 0
        if te_value > 0.3: risk = "high"
        elif te_value > 0.1: risk = "medium"
        elif te_value > 0.05 and sensitive: risk = "low"
        else: risk = "none"
        return SecurityTEResult(leakage_detected=leakage, leakage_paths=paths, risk_level=risk)
    except Exception: return None
