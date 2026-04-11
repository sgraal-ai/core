"""pydantic-ai-sgraal: Sgraal preflight validation bridge for Pydantic AI."""
from sgraal import SgraalClient


class PydanticAISgraal:
    def __init__(self, api_key: str, domain: str = "general"):
        self.client = SgraalClient(api_key)
        self.domain = domain

    def validate_messages(self, messages: list, action_type: str = "reversible") -> dict:
        memory_state = []
        for i, msg in enumerate(messages, 1):
            if hasattr(msg, 'content'):
                content = str(msg.content)
            elif isinstance(msg, dict):
                content = str(msg.get('content', msg))
            else:
                content = str(msg)
            memory_state.append({"id": f"pydantic_msg_{i:03d}", "content": content[:500], "type": "semantic",
                                 "timestamp_age_days": 0, "source_trust": 0.84, "source_conflict": 0.06, "downstream_count": 1})
        return self.client.preflight(memory_state=memory_state, domain=self.domain, action_type=action_type)

    def is_safe(self, messages: list, action_type: str = "reversible") -> bool:
        result = self.validate_messages(messages, action_type)
        return result.get("recommended_action") in ("USE_MEMORY", "WARN")
