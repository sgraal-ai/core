"""Sgraal Memory Middleware — native CrewAI integration.

Usage:
    from crewai_native import SgraalMemoryMiddleware
    middleware = SgraalMemoryMiddleware("sg_demo_playground", domain="coding")
    safe_memory = middleware.validate(agent_memory)
"""
from sgraal import SgraalClient


class SgraalMemoryMiddleware:
    """Wraps CrewAI agent memory access with Sgraal preflight validation."""

    def __init__(self, api_key: str, domain: str = "general"):
        self.client = SgraalClient(api_key)
        self.domain = domain

    def validate(self, memories: list, action_type: str = "reversible") -> list:
        memory_state = [
            {"id": f"crew_{i}", "content": str(m)[:500], "type": "semantic",
             "timestamp_age_days": 0, "source_trust": 0.82, "source_conflict": 0.08, "downstream_count": 1}
            for i, m in enumerate(memories, 1)
        ]
        result = self.client.preflight(memory_state=memory_state, domain=self.domain, action_type=action_type)
        decision = result.get("recommended_action", "USE_MEMORY") if isinstance(result, dict) else "USE_MEMORY"
        if decision == "BLOCK":
            return []
        return memories
