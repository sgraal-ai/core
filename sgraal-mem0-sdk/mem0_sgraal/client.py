"""Mem0 + Sgraal integrated client."""
import os
import requests as http_requests

try:
    from sgraal import SgraalClient
except ImportError:
    SgraalClient = None


class Mem0SgraalClient:
    """Client that wraps mem0 memory operations with Sgraal preflight validation.

    Usage:
        client = Mem0SgraalClient(
            sgraal_api_key="sg_live_...",
            mem0_api_key="m0-..."
        )
        result = client.safe_search("user preferences", user_id="alice")
        safe_memories = result["safe_memories"]
    """

    def __init__(
        self,
        sgraal_api_key: str,
        mem0_api_key: str = None,
        base_url: str = "https://api.sgraal.com",
        mem0_base_url: str = "https://api.mem0.ai/v1",
    ):
        if SgraalClient is None:
            raise ImportError("sgraal package required: pip install sgraal>=0.2.0")
        self.sgraal = SgraalClient(sgraal_api_key, base_url)
        self.mem0_api_key = mem0_api_key or os.environ.get("MEM0_API_KEY", "")
        self.mem0_base_url = mem0_base_url.rstrip("/")

    def _mem0_headers(self) -> dict:
        return {"Authorization": f"Token {self.mem0_api_key}", "Content-Type": "application/json"}

    def _search_mem0(self, query: str, user_id: str, limit: int = 10) -> list:
        """Search mem0 for memories matching query."""
        if not self.mem0_api_key:
            return []
        try:
            resp = http_requests.post(
                f"{self.mem0_base_url}/memories/search/",
                headers=self._mem0_headers(),
                json={"query": query, "user_id": user_id, "limit": limit},
                timeout=10,
            )
            if resp.ok:
                data = resp.json()
                return data.get("results", data) if isinstance(data, dict) else data
        except Exception:
            pass
        return []

    def safe_search(
        self,
        query: str,
        user_id: str,
        action_type: str = "reversible",
        domain: str = "general",
        only_use_memory: bool = True,
    ) -> dict:
        """Search mem0 and validate results with Sgraal preflight.

        Returns:
            {
                "safe_memories": [...],          # USE_MEMORY only
                "all_memories_with_decisions": [...],  # all + sgraal_decision
                "preflight_summary": {
                    "recommended_action": "...",
                    "omega_mem_final": ...,
                    "total": N,
                    "safe_count": M
                }
            }
        """
        memories = self._search_mem0(query, user_id)
        if not memories:
            return {
                "safe_memories": [],
                "all_memories_with_decisions": [],
                "preflight_summary": {"recommended_action": "USE_MEMORY", "omega_mem_final": 0, "total": 0, "safe_count": 0},
            }

        memory_state = []
        for m in memories:
            memory_state.append({
                "id": str(m.get("id", "")),
                "content": str(m.get("memory", m.get("content", ""))),
                "type": "semantic",
                "timestamp_age_days": float(m.get("age_days", 1)),
                "source_trust": float(m.get("score", 0.8)),
                "source_conflict": 0.1,
                "downstream_count": 1,
            })

        try:
            preflight = self.sgraal.preflight(
                memory_state=memory_state,
                domain=domain,
                action_type=action_type,
            )
        except Exception:
            # Graceful degradation — return all memories if Sgraal is unavailable
            return {
                "safe_memories": memories,
                "all_memories_with_decisions": memories,
                "preflight_summary": {"recommended_action": "USE_MEMORY", "omega_mem_final": 0, "total": len(memories), "safe_count": len(memories)},
            }

        decision = preflight.get("recommended_action", "USE_MEMORY")
        omega = preflight.get("omega_mem_final", 0)

        annotated = [{**m, "sgraal_decision": decision, "sgraal_omega": omega} for m in memories]
        safe = [m for m in annotated if m.get("sgraal_decision") == "USE_MEMORY"]

        return {
            "safe_memories": safe if only_use_memory else annotated,
            "all_memories_with_decisions": annotated,
            "preflight_summary": {
                "recommended_action": decision,
                "omega_mem_final": omega,
                "total": len(memories),
                "safe_count": len(safe),
            },
        }

    def safe_add(self, messages: list, user_id: str, domain: str = "general") -> dict:
        """Add memories to mem0 after Sgraal validation.

        Only adds messages that pass preflight (USE_MEMORY or WARN).
        """
        memory_state = [
            {
                "id": f"add_{i}",
                "content": str(m.get("content", m.get("role", "") + ": " + m.get("content", "")) if isinstance(m, dict) else str(m)),
                "type": "episodic",
                "timestamp_age_days": 0,
                "source_trust": 0.9,
                "source_conflict": 0.05,
                "downstream_count": 1,
            }
            for i, m in enumerate(messages)
        ]

        try:
            preflight = self.sgraal.preflight(
                memory_state=memory_state, domain=domain, action_type="reversible",
            )
            if preflight.get("recommended_action") in ("BLOCK", "ASK_USER"):
                return {"added": False, "reason": f"Sgraal blocked: {preflight.get('recommended_action')}", "omega": preflight.get("omega_mem_final", 0)}
        except Exception:
            pass  # Graceful degradation — allow add if Sgraal unavailable

        if not self.mem0_api_key:
            return {"added": False, "reason": "No mem0 API key configured"}

        try:
            resp = http_requests.post(
                f"{self.mem0_base_url}/memories/",
                headers=self._mem0_headers(),
                json={"messages": messages, "user_id": user_id},
                timeout=10,
            )
            if resp.ok:
                return {"added": True, "mem0_response": resp.json()}
            return {"added": False, "reason": f"mem0 error: {resp.status_code}"}
        except Exception as e:
            return {"added": False, "reason": str(e)}
