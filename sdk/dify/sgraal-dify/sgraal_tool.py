"""Sgraal Preflight — Dify custom tool for memory governance."""
import requests

TOOL_DEFINITION = {
    "name": "sgraal_preflight",
    "description": "Validate AI agent memory before action. Returns USE_MEMORY/WARN/ASK_USER/BLOCK.",
    "parameters": [
        {"name": "memory_state", "type": "string", "required": True, "description": "JSON array of memory entries"},
        {"name": "domain", "type": "string", "required": False, "default": "general"},
        {"name": "action_type", "type": "string", "required": False, "default": "reversible"},
    ],
}

def run(memory_state: str, domain: str = "general", action_type: str = "reversible", api_key: str = "sg_demo_playground") -> dict:
    import json
    resp = requests.post("https://api.sgraal.com/v1/preflight",
        json={"memory_state": json.loads(memory_state), "domain": domain, "action_type": action_type},
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, timeout=30)
    data = resp.json()
    return {"recommended_action": data.get("recommended_action"), "omega": data.get("omega_mem_final"),
            "attack_surface_level": data.get("attack_surface_level")}
