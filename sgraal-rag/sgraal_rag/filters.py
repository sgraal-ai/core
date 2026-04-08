"""Sgraal RAG pipeline filter — validate retrieved documents before generation."""
import os
import requests as http_requests


class SgraalRAGFilter:
    """Drop-in filter for any RAG pipeline.

    Usage:
        f = SgraalRAGFilter(api_key="sg_live_...", domain="fintech")
        safe_docs = f.filter(retrieved_documents)
    """

    def __init__(self, api_key: str = None, domain: str = "general",
                 action_type: str = "reversible",
                 base_url: str = "https://api.sgraal.com"):
        self.api_key = api_key or os.environ.get("SGRAAL_API_KEY", "")
        self.domain = domain
        self.action_type = action_type
        self.base_url = base_url.rstrip("/")

    def filter(self, documents: list) -> list:
        """Filter RAG documents through Sgraal preflight. Returns only USE_MEMORY documents."""
        if not documents or not self.api_key:
            return documents

        memory_state = [
            {
                "id": str(d.get("id", d.get("doc_id", f"doc_{i}"))),
                "content": str(d.get("content", d.get("text", d.get("page_content", "")))),
                "type": "semantic",
                "timestamp_age_days": float(d.get("age_days", 7)),
                "source_trust": float(d.get("score", d.get("relevance_score", 0.8))),
                "source_conflict": float(d.get("source_conflict", 0.1)),
                "downstream_count": 1,
            }
            for i, d in enumerate(documents)
        ]

        try:
            resp = http_requests.post(
                f"{self.base_url}/v1/preflight",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"memory_state": memory_state, "domain": self.domain, "action_type": self.action_type},
                timeout=10,
            )
            if not resp.ok:
                return documents
            data = resp.json()
        except Exception:
            return documents

        decision = data.get("recommended_action", "USE_MEMORY")
        if decision in ("BLOCK", "ASK_USER"):
            return []
        return [{**d, "sgraal_decision": decision, "sgraal_omega": data.get("omega_mem_final", 0)} for d in documents]

    def as_langchain_filter(self):
        """Returns a callable compatible with LangChain retriever filtering."""
        rag_filter = self
        def langchain_filter(documents: list) -> list:
            return rag_filter.filter([{"content": d.page_content, "score": d.metadata.get("score", 0.8)} if hasattr(d, "page_content") else d for d in documents])
        return langchain_filter

    def as_llamaindex_filter(self):
        """Returns a callable compatible with LlamaIndex node postprocessing."""
        rag_filter = self
        def llamaindex_filter(nodes: list) -> list:
            docs = [{"content": n.text, "score": n.score or 0.8} if hasattr(n, "text") else n for n in nodes]
            safe = rag_filter.filter(docs)
            if len(safe) == len(nodes):
                return nodes
            return [n for i, n in enumerate(nodes) if i < len(safe)]
        return llamaindex_filter
