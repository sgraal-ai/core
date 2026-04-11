"""vercel-ai-sgraal: Sgraal preflight validation bridge for Vercel AI SDK."""
from sgraal import SgraalClient


class VercelAISgraal:
    def __init__(self, api_key: str, domain: str = "general"):
        self.client = SgraalClient(api_key)
        self.domain = domain

    def validate_context(self, context, action_type: str = "informational") -> dict:
        if isinstance(context, str):
            context = [context]
        memory_state = [
            {"id": f"vercel_ctx_{i:03d}", "content": c[:500], "type": "semantic",
             "timestamp_age_days": 0, "source_trust": 0.85, "source_conflict": 0.05, "downstream_count": 1}
            for i, c in enumerate(context, 1)
        ]
        return self.client.preflight(memory_state=memory_state, domain=self.domain, action_type=action_type)

    def is_safe(self, context, action_type: str = "informational") -> bool:
        result = self.validate_context(context, action_type)
        return result.get("recommended_action") in ("USE_MEMORY", "WARN")
