"""semantic-kernel-sgraal: Sgraal preflight validation bridge for Microsoft Semantic Kernel."""
from sgraal import SgraalClient


class SemanticKernelSgraal:
    def __init__(self, api_key: str, domain: str = "general"):
        self.client = SgraalClient(api_key)
        self.domain = domain

    def validate_memories(self, memories: list, action_type: str = "reversible") -> dict:
        memory_state = [
            {"id": f"sk_memory_{i:03d}", "content": str(m)[:500], "type": "semantic",
             "timestamp_age_days": 0, "source_trust": 0.82, "source_conflict": 0.08, "downstream_count": 1}
            for i, m in enumerate(memories, 1)
        ]
        return self.client.preflight(memory_state=memory_state, domain=self.domain, action_type=action_type)

    def is_safe(self, memories: list, action_type: str = "reversible") -> bool:
        result = self.validate_memories(memories, action_type)
        return result.get("recommended_action") in ("USE_MEMORY", "WARN")
