"""Sgraal filter for Microsoft Semantic Kernel."""
from __future__ import annotations

class SgraalSemanticKernelFilter:
    def __init__(self, api_key: str, api_url: str = "https://api.sgraal.com"):
        self.api_key, self.api_url = api_key, api_url

    def filter(self, memory_entries: list) -> list:
        return [e for e in memory_entries if e.get("omega_score", 0) <= 80]
