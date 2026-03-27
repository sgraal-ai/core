"""Sgraal node for Haystack pipelines."""
from __future__ import annotations

class SgraalHaystackNode:
    def __init__(self, api_key: str, api_url: str = "https://api.sgraal.com"):
        self.api_key, self.api_url = api_key, api_url

    def run(self, documents: list) -> dict:
        filtered = [d for d in documents if d.get("omega_score", 0) <= 80]
        return {"documents": filtered, "filtered_count": len(documents) - len(filtered)}
