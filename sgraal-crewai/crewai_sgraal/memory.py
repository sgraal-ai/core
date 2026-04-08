"""Sgraal memory guard for CrewAI agents."""
import os
import requests as http_requests


class SgraalMemoryGuard:
    """Drop-in memory validator for CrewAI agents.

    Usage:
        guard = SgraalMemoryGuard(api_key="sg_live_...", domain="fintech")
        safe = guard.validate(memories, action_type="irreversible")
    """

    def __init__(self, api_key: str = None, domain: str = "general",
                 base_url: str = "https://api.sgraal.com"):
        self.api_key = api_key or os.environ.get("SGRAAL_API_KEY", "")
        self.domain = domain
        self.base_url = base_url.rstrip("/")

    def validate(self, memories: list, action_type: str = "reversible") -> list:
        """Run preflight on CrewAI memory entries. Returns only safe memories."""
        if not memories or not self.api_key:
            return memories

        memory_state = [
            {
                "id": str(m.get("id", f"crew_{i}")),
                "content": str(m.get("content", m.get("memory", m.get("description", "")))),
                "type": "semantic",
                "timestamp_age_days": float(m.get("age_days", 1)),
                "source_trust": float(m.get("score", m.get("relevance", 0.8))),
                "source_conflict": 0.1,
                "downstream_count": 1,
            }
            for i, m in enumerate(memories)
        ]

        try:
            resp = http_requests.post(
                f"{self.base_url}/v1/preflight",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"memory_state": memory_state, "domain": self.domain, "action_type": action_type},
                timeout=10,
            )
            if not resp.ok:
                return memories
            data = resp.json()
        except Exception:
            return memories

        decision = data.get("recommended_action", "USE_MEMORY")
        if decision in ("BLOCK", "ASK_USER"):
            return []
        return [{**m, "sgraal_decision": decision, "sgraal_omega": data.get("omega_mem_final", 0)} for m in memories]

    def as_tool(self):
        """Returns a dict compatible with CrewAI tool registration."""
        guard = self
        def validate_memory(memories: str) -> str:
            import json
            try:
                parsed = json.loads(memories) if isinstance(memories, str) else memories
                safe = guard.validate(parsed if isinstance(parsed, list) else [parsed])
                return json.dumps({"safe_count": len(safe), "total": len(parsed) if isinstance(parsed, list) else 1, "decision": safe[0].get("sgraal_decision", "USE_MEMORY") if safe else "BLOCK"})
            except Exception as e:
                return json.dumps({"error": str(e)})
        return {"name": "sgraal_memory_validator", "description": "Validate agent memory with Sgraal preflight", "func": validate_memory}
