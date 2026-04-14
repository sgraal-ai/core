"""Example: Guard OpenAI function calls with Sgraal preflight."""
import os
from openai_sgraal import preflight_hook

SGRAAL_KEY = os.environ.get("SGRAAL_API_KEY", "sg_demo_playground")

# Simulate agent memory
agent_memory = [
    {"id": "tx_limit", "content": "Daily transfer limit: $10,000",
     "type": "policy", "timestamp_age_days": 90, "source_trust": 0.6,
     "source_conflict": 0.3, "downstream_count": 20},
]

# Before executing a tool call, check memory governance
decision = preflight_hook(
    api_key=SGRAAL_KEY,
    memory_state=agent_memory,
    domain="fintech",
    action_type="irreversible",
)

action = decision.get("recommended_action", "USE_MEMORY")
omega = decision.get("omega_mem_final", 0)

if action == "BLOCK":
    print(f"BLOCKED: omega={omega}")
    print(f"Reason: {decision.get('explainability_note')}")
    print(f"Repair plan: {decision.get('repair_plan', [])[:2]}")
elif action in ("WARN", "ASK_USER"):
    print(f"WARNING: omega={omega}, proceeding with caution")
else:
    print(f"SAFE: omega={omega}, executing function call")
