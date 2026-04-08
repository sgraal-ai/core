"""Sgraal memory middleware for AutoGen agents."""
import os
import requests as http_requests


class SgraalMemoryMiddleware:
    """Validate AutoGen agent context/memory before execution.

    Usage:
        mw = SgraalMemoryMiddleware(api_key="sg_live_...", domain="coding")
        safe_ctx = mw.validate_context(agent_context)
    """

    def __init__(self, api_key: str = None, domain: str = "general",
                 base_url: str = "https://api.sgraal.com"):
        self.api_key = api_key or os.environ.get("SGRAAL_API_KEY", "")
        self.domain = domain
        self.base_url = base_url.rstrip("/")

    def validate_context(self, context: dict, action_type: str = "reversible") -> dict:
        """Validate AutoGen agent context. Returns filtered context with sgraal annotations."""
        if not context or not self.api_key:
            return context

        # Extract memory entries from AutoGen context
        messages = context.get("messages", context.get("chat_history", []))
        if not isinstance(messages, list):
            messages = [messages] if messages else []

        memory_state = [
            {
                "id": f"autogen_{i}",
                "content": str(m.get("content", m) if isinstance(m, dict) else str(m)),
                "type": "episodic",
                "timestamp_age_days": 0,
                "source_trust": 0.8,
                "source_conflict": 0.05,
                "downstream_count": 1,
            }
            for i, m in enumerate(messages)
        ]

        if not memory_state:
            return context

        try:
            resp = http_requests.post(
                f"{self.base_url}/v1/preflight",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"memory_state": memory_state, "domain": self.domain, "action_type": action_type},
                timeout=10,
            )
            if not resp.ok:
                return context
            data = resp.json()
        except Exception:
            return context

        decision = data.get("recommended_action", "USE_MEMORY")
        omega = data.get("omega_mem_final", 0)

        return {
            **context,
            "sgraal_decision": decision,
            "sgraal_omega": omega,
            "sgraal_safe": decision in ("USE_MEMORY", "WARN"),
        }
