"""Sgraal Python SDK client."""
import requests
from typing import Optional


class SgraalClient:
    """Client for the Sgraal Memory Governance API.

    Usage:
        client = SgraalClient(api_key="sg_live_...")
        result = client.preflight(
            memory_state=[{"id": "m1", "content": "test", "type": "semantic",
                           "timestamp_age_days": 1, "source_trust": 0.9}],
            domain="general",
            action_type="reversible"
        )
        print(result["recommended_action"])
    """

    def __init__(self, api_key: str, base_url: str = "https://api.sgraal.com"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _post(self, path: str, body: dict, timeout: int = 15) -> dict:
        resp = requests.post(
            f"{self.base_url}{path}",
            headers=self._headers(),
            json=body,
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str, params: Optional[dict] = None, timeout: int = 10) -> dict:
        resp = requests.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            params=params,
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def preflight(
        self,
        memory_state: list,
        domain: str = "general",
        action_type: str = "reversible",
        **kwargs,
    ) -> dict:
        """Run a preflight check on memory state.

        Returns omega_mem_final, recommended_action, component_breakdown,
        repair_plan, and 80+ analytics fields.
        """
        body = {
            "memory_state": memory_state,
            "domain": domain,
            "action_type": action_type,
            **kwargs,
        }
        return self._post("/v1/preflight", body)

    def heal(
        self,
        entry_id: str,
        action: str,
        agent_id: Optional[str] = None,
    ) -> dict:
        """Heal a memory entry by applying a repair action.

        Actions: REFETCH, VERIFY_WITH_SOURCE, REBUILD_WORKING_SET.
        """
        body = {"entry_id": entry_id, "action": action}
        if agent_id:
            body["agent_id"] = agent_id
        return self._post("/v1/heal", body)

    def explain(
        self,
        preflight_result: dict,
        audience: str = "developer",
        language: str = "en",
    ) -> dict:
        """Get a natural language explanation of a preflight result.

        Audiences: developer, compliance, executive.
        """
        return self._post("/v1/explain", {
            "preflight_result": preflight_result,
            "audience": audience,
            "language": language,
        })

    def compare_grok(
        self,
        sgraal_decision: str,
        grok_decision: str,
        omega: float,
        domain: str = "general",
    ) -> dict:
        """Compare Sgraal and Grok decisions for the same memory state."""
        return self._post("/v1/compare/grok", {
            "sgraal_decision": sgraal_decision,
            "grok_decision": grok_decision,
            "omega": omega,
            "domain": domain,
        })

    def propagation_trace(
        self,
        agent_id: str,
        memory_state: list,
        domain: str = "general",
    ) -> dict:
        """Trace how memory propagates across agents."""
        return self._post("/v1/propagation/trace", {
            "agent_id": agent_id,
            "memory_state": memory_state,
            "domain": domain,
        })

    def fidelity_certify(
        self,
        memory_state: list,
        domain: str = "general",
    ) -> dict:
        """Certify the fidelity of a memory state."""
        return self._post("/v1/fidelity/certify", {
            "memory_state": memory_state,
            "domain": domain,
        })
