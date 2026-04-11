"""mngr-sgraal: Sgraal preflight validation bridge for mngr (Imbue) parallel agent runner."""
from sgraal import SgraalClient


class MngrSgraal:
    def __init__(self, api_key: str, domain: str = "general"):
        self.client = SgraalClient(api_key)
        self.domain = domain

    def validate_agent_output(self, agent_id: str, output: str,
                               action_type: str = "reversible") -> dict:
        """Validate output from one mngr agent before passing to another."""
        memory_state = [{
            "id": f"mngr_{agent_id}_output",
            "content": output[:500],
            "type": "semantic",
            "timestamp_age_days": 0,
            "source_trust": 0.82,
            "source_conflict": 0.08,
            "downstream_count": 1,
            "provenance_chain": [agent_id]
        }]
        return self.client.preflight(
            memory_state=memory_state,
            domain=self.domain,
            action_type=action_type
        )

    def validate_parallel_outputs(self, outputs: dict,
                                   action_type: str = "reversible") -> dict:
        """Validate outputs from multiple parallel mngr agents."""
        memory_state = [
            {
                "id": f"mngr_{agent_id}_output",
                "content": output[:500],
                "type": "semantic",
                "timestamp_age_days": 0,
                "source_trust": 0.82,
                "source_conflict": 0.05,
                "downstream_count": 2,
                "provenance_chain": [agent_id]
            }
            for agent_id, output in outputs.items()
        ]
        return self.client.preflight(
            memory_state=memory_state,
            domain=self.domain,
            action_type=action_type
        )

    def is_safe(self, agent_id: str, output: str,
                action_type: str = "reversible") -> bool:
        result = self.validate_agent_output(agent_id, output, action_type)
        return result.get("recommended_action") in ("USE_MEMORY", "WARN")
