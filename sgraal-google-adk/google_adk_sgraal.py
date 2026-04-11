"""google-adk-sgraal: Sgraal preflight validation bridge for Google Agent Development Kit."""
from sgraal import SgraalClient


class GoogleADKSgraal:
    def __init__(self, api_key: str, domain: str = "general"):
        self.client = SgraalClient(api_key)
        self.domain = domain

    def validate_state(self, state, action_type: str = "reversible") -> dict:
        if isinstance(state, dict):
            entries = [{"key": k, "value": str(v)} for k, v in state.items()]
        else:
            entries = state
        memory_state = [
            {"id": f"adk_state_{i:03d}", "content": str(e)[:500], "type": "semantic",
             "timestamp_age_days": 0, "source_trust": 0.86, "source_conflict": 0.05, "downstream_count": 1}
            for i, e in enumerate(entries, 1)
        ]
        return self.client.preflight(memory_state=memory_state, domain=self.domain, action_type=action_type)

    def validate_tool_context(self, tool_context: list, action_type: str = "irreversible") -> dict:
        memory_state = [
            {"id": f"adk_tool_{i:03d}", "content": ctx[:500], "type": "semantic",
             "timestamp_age_days": 0, "source_trust": 0.87, "source_conflict": 0.05, "downstream_count": 3}
            for i, ctx in enumerate(tool_context, 1)
        ]
        return self.client.preflight(memory_state=memory_state, domain=self.domain, action_type=action_type)

    def is_safe(self, state, action_type: str = "reversible") -> bool:
        result = self.validate_state(state, action_type)
        return result.get("recommended_action") in ("USE_MEMORY", "WARN")
