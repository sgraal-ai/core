"""Example: OpenAI Assistants API with Sgraal memory governance."""
import os
from openai_sgraal import preflight_hook

SGRAAL_KEY = os.environ.get("SGRAAL_API_KEY", "sg_demo_playground")

# Medical agent memory — high stakes
memory = [
    {"id": "allergy", "content": "Patient allergic to penicillin",
     "type": "semantic", "timestamp_age_days": 45, "source_trust": 0.85,
     "source_conflict": 0.15, "downstream_count": 12},
    {"id": "dosage", "content": "Current dosage: amoxicillin 500mg",
     "type": "tool_state", "timestamp_age_days": 2, "source_trust": 0.7,
     "source_conflict": 0.2, "downstream_count": 8},
    {"id": "protocol", "content": "Treatment protocol v3.2 (updated Q1 2026)",
     "type": "policy", "timestamp_age_days": 60, "source_trust": 0.9,
     "source_conflict": 0.05, "downstream_count": 15},
]

# Run preflight before assistant acts on memory
decision = preflight_hook(
    api_key=SGRAAL_KEY,
    memory_state=memory,
    domain="medical",
    action_type="irreversible",
)

print(f"Omega: {decision.get('omega_mem_final')}")
print(f"Decision: {decision.get('recommended_action')}")
print(f"Days until BLOCK: {decision.get('days_until_block')}")
print(f"Knowledge age: {decision.get('knowledge_age_days')} days")
print(f"Monoculture risk: {decision.get('monoculture_risk_level')}")

if decision.get("recommended_action") == "BLOCK":
    print("\nAssistant BLOCKED from acting on this memory.")
    print(f"Reason: {decision.get('explainability_note')}")
    repair = decision.get("repair_plan", [])
    if repair:
        print(f"Fix: {repair[0].get('action')} on {repair[0].get('entry_id')}")
else:
    print("\nMemory governance passed. Safe to proceed with assistant.")
