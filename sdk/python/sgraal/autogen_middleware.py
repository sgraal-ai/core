"""Sgraal middleware for AutoGen agents."""
from __future__ import annotations
import warnings
from typing import Optional

class SgraalAutoGenMiddleware:
    def __init__(self, api_key: str, api_url: str = "https://api.sgraal.com", on_block: str = "warn"):
        self.api_key, self.api_url, self.on_block = api_key, api_url, on_block

    def intercept(self, message: dict) -> Optional[dict]:
        ms = message.get("memory_state")
        if not ms: return None
        import requests
        r = requests.post(f"{self.api_url}/v1/preflight", json={"memory_state": ms},
            headers={"Authorization": f"Bearer {self.api_key}"}, timeout=10)
        result = r.json()
        action = result.get("recommended_action", "USE_MEMORY")
        if action == "BLOCK":
            if self.on_block == "raise": raise RuntimeError(f"Sgraal BLOCK")
            warnings.warn("Sgraal BLOCK", UserWarning, stacklevel=2)
        return result
