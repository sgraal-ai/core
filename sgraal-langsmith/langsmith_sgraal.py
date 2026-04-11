"""langsmith-sgraal: Sgraal preflight decisions as LangSmith trace spans."""
from sgraal import SgraalClient


class LangSmithSgraal:
    def __init__(self, api_key: str, domain: str = "general",
                 langsmith_project: str = "sgraal-decisions"):
        self.client = SgraalClient(api_key)
        self.domain = domain
        self.project = langsmith_project

    def preflight_with_trace(self, memory_state: list, action_type: str = "reversible",
                              run_name: str = "sgraal_preflight") -> dict:
        result = self.client.preflight(memory_state=memory_state, domain=self.domain, action_type=action_type)
        trace = {
            "name": run_name, "run_type": "tool", "project_name": self.project,
            "inputs": {"memory_entries": len(memory_state), "domain": self.domain, "action_type": action_type},
            "outputs": {
                "decision": result.get("recommended_action"),
                "omega": result.get("omega_mem_final"),
                "attack_surface_level": result.get("attack_surface_level"),
                "timestamp_integrity": result.get("timestamp_integrity"),
                "identity_drift": result.get("identity_drift"),
                "consensus_collapse": result.get("consensus_collapse"),
                "naturalness_level": result.get("naturalness_level"),
            },
            "tags": ["sgraal", f"decision:{result.get('recommended_action', 'UNKNOWN')}"]
        }
        result["langsmith_trace"] = trace
        return result
