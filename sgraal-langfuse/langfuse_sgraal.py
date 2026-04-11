"""langfuse-sgraal: Sgraal preflight decisions as Langfuse trace spans."""
from sgraal import SgraalClient


class LangfuseSgraal:
    def __init__(self, api_key: str, domain: str = "general"):
        self.client = SgraalClient(api_key)
        self.domain = domain

    def preflight_with_trace(self, memory_state: list, action_type: str = "reversible",
                              trace_name: str = "sgraal_preflight") -> dict:
        result = self.client.preflight(memory_state=memory_state, domain=self.domain, action_type=action_type)
        trace = {
            "name": trace_name,
            "input": {"memory_entries": len(memory_state), "domain": self.domain, "action_type": action_type},
            "output": {
                "decision": result.get("recommended_action"),
                "omega": result.get("omega_mem_final"),
                "attack_surface_level": result.get("attack_surface_level"),
                "naturalness_level": result.get("naturalness_level"),
                "active_detection_layers": result.get("active_detection_layers", []),
            },
            "metadata": {"sgraal_request_id": result.get("request_id"), "deterministic": result.get("deterministic", True)},
            "tags": ["sgraal", result.get("recommended_action", "UNKNOWN")]
        }
        result["langfuse_trace"] = trace
        return result
