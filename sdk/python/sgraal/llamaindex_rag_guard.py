"""Sgraal RAG Guard for LlamaIndex — wraps any query engine with omega filtering."""
from __future__ import annotations
from typing import Optional


class SgraalQueryEngineWrapper:
    """Wrap a LlamaIndex-style query engine with Sgraal omega scoring.

    Usage:
        from sgraal.llamaindex_rag_guard import SgraalQueryEngineWrapper
        wrapper = SgraalQueryEngineWrapper(engine, api_key="sg_live_...", max_omega=60)
        safe_nodes = wrapper.retrieve("query")
    """

    def __init__(self, engine=None, api_key: str = "",
                 api_url: str = "https://api.sgraal.com", max_omega: float = 60):
        self.engine = engine
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.max_omega = max_omega

    def retrieve(self, query: str) -> list:
        """Retrieve and filter nodes by omega score."""
        if not self.engine:
            return []
        nodes = self.engine.retrieve(query) if hasattr(self.engine, "retrieve") else []
        filtered = []
        for node in nodes:
            content = getattr(node, "text", str(node))
            omega = self._score(content)
            if omega <= self.max_omega:
                if hasattr(node, "metadata"):
                    node.metadata["sgraal_omega"] = omega
                filtered.append(node)
        return filtered

    def _score(self, content: str) -> float:
        if len(content) < 10:
            return 0.0
        try:
            import requests
            r = requests.post(f"{self.api_url}/v1/preflight",
                json={"memory_state": [{"id": "rag", "content": content, "type": "semantic",
                    "timestamp_age_days": 0, "source_trust": 0.8, "source_conflict": 0.1,
                    "downstream_count": 1}]},
                headers={"Authorization": f"Bearer {self.api_key}"}, timeout=5)
            return r.json().get("omega_mem_final", 0)
        except Exception:
            return 0.0
