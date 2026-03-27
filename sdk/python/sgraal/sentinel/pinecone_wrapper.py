"""Sgraal Sentinel wrapper — filters high-omega results."""
from __future__ import annotations

class SgraalVectorGuard:
    def __init__(self, client, api_key: str, max_omega: float = 80):
        self.client, self.api_key, self.max_omega = client, api_key, max_omega
    def query(self, *args, **kwargs):
        results = self.client.query(*args, **kwargs) if self.client else []
        return [r for r in results if r.get("omega_score", 0) <= self.max_omega]
