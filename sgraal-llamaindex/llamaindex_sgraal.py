"""llamaindex-sgraal: Sgraal preflight validation bridge for LlamaIndex."""
from sgraal import SgraalClient


class LlamaIndexSgraal:
    def __init__(self, api_key: str, domain: str = "general"):
        self.client = SgraalClient(api_key)
        self.domain = domain

    def validate_nodes(self, nodes: list, action_type: str = "informational") -> dict:
        memory_state = []
        for i, node in enumerate(nodes, 1):
            if hasattr(node, 'get_content'):
                content = node.get_content()
            elif hasattr(node, 'text'):
                content = node.text
            else:
                content = str(node)
            memory_state.append({
                "id": f"llamaindex_node_{i:03d}", "content": content[:500],
                "type": "semantic", "timestamp_age_days": 0,
                "source_trust": 0.85, "source_conflict": 0.05, "downstream_count": 1
            })
        return self.client.preflight(memory_state=memory_state, domain=self.domain, action_type=action_type)

    def filter_safe_nodes(self, nodes: list, action_type: str = "informational") -> list:
        if not nodes:
            return []
        result = self.validate_nodes(nodes, action_type)
        return nodes if result.get("recommended_action") in ("USE_MEMORY", "WARN") else []

    def is_safe(self, nodes: list, action_type: str = "informational") -> bool:
        result = self.validate_nodes(nodes, action_type)
        return result.get("recommended_action") in ("USE_MEMORY", "WARN")
