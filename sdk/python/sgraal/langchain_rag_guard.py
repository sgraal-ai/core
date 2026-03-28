"""Sgraal RAG Guard for LangChain — wraps any BaseRetriever with omega filtering."""
from __future__ import annotations
from typing import Optional


class SgraalRAGGuard:
    """Wrap a LangChain-style retriever with Sgraal omega scoring.

    Usage:
        from sgraal.langchain_rag_guard import SgraalRAGGuard
        guard = SgraalRAGGuard(retriever, api_key="sg_live_...", max_omega=60)
        safe_docs = guard.get_relevant_documents("query")
    """

    def __init__(self, retriever, api_key: str = "",
                 api_url: str = "https://api.sgraal.com", max_omega: float = 60):
        self.retriever = retriever
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.max_omega = max_omega

    def get_relevant_documents(self, query: str) -> list:
        """Retrieve and filter documents by omega score."""
        docs = self.retriever.get_relevant_documents(query) if self.retriever else []
        if not docs:
            return docs
        filtered = []
        for doc in docs:
            content = getattr(doc, "page_content", "") if hasattr(doc, "page_content") else str(doc)
            omega = self._score(content)
            if omega <= self.max_omega:
                if hasattr(doc, "metadata"):
                    doc.metadata["sgraal_omega"] = omega
                filtered.append(doc)
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
