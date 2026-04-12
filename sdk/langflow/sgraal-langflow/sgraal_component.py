"""Sgraal Memory Governance — Langflow custom component."""
import requests
import json

class SgraalMemoryGovernance:
    display_name = "Sgraal Memory Governance"
    description = "Validate AI agent memory before action with Sgraal preflight."

    def build(self, memory_state: str, domain: str = "general", action_type: str = "reversible", api_key: str = "sg_demo_playground") -> dict:
        resp = requests.post("https://api.sgraal.com/v1/preflight",
            json={"memory_state": json.loads(memory_state), "domain": domain, "action_type": action_type},
            headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
        return resp.json()
