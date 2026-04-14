"""Example: Basic memory governance with OpenAI completions."""
import os
from openai_sgraal import OpenAISgraalClient

client = OpenAISgraalClient(
    sgraal_api_key=os.environ.get("SGRAAL_API_KEY", "sg_demo_playground"),
    openai_api_key=os.environ.get("OPENAI_API_KEY"),
)

# Agent memory: what the agent "knows"
memory = [
    {"id": "balance", "content": "Account balance: $85,000 as of today",
     "type": "tool_state", "timestamp_age_days": 0.1, "source_trust": 0.95,
     "source_conflict": 0.02, "downstream_count": 5},
    {"id": "risk_pref", "content": "Client risk tolerance: moderate",
     "type": "preference", "timestamp_age_days": 30, "source_trust": 0.8,
     "source_conflict": 0.1, "downstream_count": 3},
]

# Run governed completion
result = client.safe_complete(
    messages=[{"role": "user", "content": "Should I invest in crypto?"}],
    memory=memory,
    model="gpt-4o",
    domain="fintech",
    action_type="reversible",
)

print(f"Decision: {result.preflight.get('recommended_action')}")
print(f"Omega: {result.preflight.get('omega_mem_final')}")
print(f"Knowledge age: {result.preflight.get('knowledge_age_days')} days")
