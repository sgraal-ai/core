"""Sgraal guard for CrewAI agents."""
from __future__ import annotations
import warnings
from typing import Optional

class SgraalBlockedError(Exception): pass

class SgraalCrewAIGuard:
    def __init__(self, api_key: str, api_url: str = "https://api.sgraal.com", on_block: str = "raise"):
        self.api_key, self.api_url, self.on_block = api_key, api_url, on_block

    def check(self, memory_state: Optional[list] = None) -> Optional[dict]:
        if not memory_state: return None
        import requests
        r = requests.post(f"{self.api_url}/v1/preflight", json={"memory_state": memory_state},
            headers={"Authorization": f"Bearer {self.api_key}"}, timeout=10)
        result = r.json()
        if result.get("recommended_action") == "BLOCK":
            if self.on_block == "raise": raise SgraalBlockedError(f"BLOCK: omega={result.get('omega_mem_final')}")
            elif self.on_block == "warn": warnings.warn("Sgraal BLOCK", UserWarning, stacklevel=2)
        return result

def sgraal_guard(api_key: str, on_block: str = "raise"):
    def decorator(fn):
        guard = SgraalCrewAIGuard(api_key, on_block=on_block)
        def wrapper(*args, **kwargs):
            ms = kwargs.get("memory_state")
            if ms: guard.check(ms)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
