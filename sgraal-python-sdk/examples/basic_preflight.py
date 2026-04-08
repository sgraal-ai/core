"""Basic preflight example using the Sgraal SDK."""
import os
from sgraal import SgraalClient

client = SgraalClient(
    api_key=os.environ.get("SGRAAL_API_KEY", "sg_demo_playground")
)

result = client.preflight(
    memory_state=[
        {
            "id": "mem_001",
            "content": "Account balance: $50,000",
            "type": "tool_state",
            "timestamp_age_days": 3,
            "source_trust": 0.92,
            "source_conflict": 0.08,
            "downstream_count": 5,
        }
    ],
    domain="fintech",
    action_type="irreversible",
)

action = result["recommended_action"]
omega = result["omega_mem_final"]

print(f"Decision: {action}")
print(f"Omega: {omega}")

if action == "BLOCK":
    print("Memory too risky — do not proceed")
elif action == "WARN":
    print("Proceed with caution")
elif action == "ASK_USER":
    print("Human approval required")
else:
    print("Safe to proceed")
