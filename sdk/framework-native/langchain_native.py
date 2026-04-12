"""Sgraal Memory Governor — native LangChain callback handler.

Usage:
    from langchain_native import SgraalMemoryGovernor
    llm = ChatOpenAI(callbacks=[SgraalMemoryGovernor("sg_demo_playground")])
"""
from sgraal import SgraalClient


class BlockedMemoryError(Exception):
    """Raised when Sgraal blocks a memory access."""
    pass


class SgraalMemoryGovernor:
    """LangChain callback handler that validates retrieved documents via Sgraal."""

    def __init__(self, api_key: str, domain: str = "general", block_on_warn: bool = False):
        self.client = SgraalClient(api_key)
        self.domain = domain
        self.block_on_warn = block_on_warn

    def on_retriever_end(self, documents, **kwargs):
        memory_state = [
            {"id": f"doc_{i}", "content": getattr(doc, "page_content", str(doc))[:500],
             "type": "semantic", "timestamp_age_days": 0, "source_trust": 0.85,
             "source_conflict": 0.05, "downstream_count": 1}
            for i, doc in enumerate(documents, 1)
        ]
        if not memory_state:
            return
        result = self.client.preflight(memory_state=memory_state, domain=self.domain, action_type="informational")
        decision = result.get("recommended_action", "USE_MEMORY") if isinstance(result, dict) else "USE_MEMORY"
        if decision == "BLOCK":
            raise BlockedMemoryError(f"Sgraal BLOCK: omega={result.get('omega_mem_final')}")
        if decision in ("WARN", "ASK_USER") and self.block_on_warn:
            raise BlockedMemoryError(f"Sgraal {decision}: omega={result.get('omega_mem_final')}")
