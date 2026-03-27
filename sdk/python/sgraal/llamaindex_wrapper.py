"""Sgraal wrapper for LlamaIndex retrievers — filters high-omega results."""
from __future__ import annotations
from typing import Optional

class SgraalRetrieverWrapper:
    def __init__(self, retriever, api_key: str, api_url: str = "https://api.sgraal.com", max_omega: float = 80):
        self.retriever, self.api_key, self.api_url, self.max_omega = retriever, api_key, api_url, max_omega

    def retrieve(self, query: str) -> list:
        results = self.retriever.retrieve(query) if self.retriever else []
        return [r for r in results if r.get("omega_score", 0) <= self.max_omega]
