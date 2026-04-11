"""azure-ai-sgraal: Sgraal preflight validation bridge for Azure AI Foundry."""
from sgraal import SgraalClient


class AzureAISgraal:
    def __init__(self, api_key: str, domain: str = "general"):
        self.client = SgraalClient(api_key)
        self.domain = domain

    def validate_messages(self, messages: list, action_type: str = "reversible") -> dict:
        memory_state = [
            {"id": f"azure_msg_{i:03d}", "content": str(msg.get("content", msg))[:500],
             "type": "semantic", "timestamp_age_days": 0, "source_trust": 0.84,
             "source_conflict": 0.06, "downstream_count": 1}
            for i, msg in enumerate(messages, 1)
            if not isinstance(msg, dict) or msg.get("role") != "system"
        ]
        if not memory_state:
            return {"recommended_action": "USE_MEMORY", "skipped": True}
        return self.client.preflight(memory_state=memory_state, domain=self.domain, action_type=action_type)

    def validate_tool_result(self, tool_name: str, result: str, action_type: str = "irreversible") -> dict:
        memory_state = [{"id": f"azure_tool_{tool_name}", "content": result[:500], "type": "semantic",
                         "timestamp_age_days": 0, "source_trust": 0.88, "source_conflict": 0.04, "downstream_count": 3}]
        return self.client.preflight(memory_state=memory_state, domain=self.domain, action_type=action_type)

    def is_safe(self, messages: list, action_type: str = "reversible") -> bool:
        result = self.validate_messages(messages, action_type)
        return result.get("recommended_action") in ("USE_MEMORY", "WARN")
