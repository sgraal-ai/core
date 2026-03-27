"""Fintech Trading Agent with Sgraal Memory Governance.

Before every trade decision, the agent runs a Sgraal preflight check
to ensure its memory (market data, risk models, compliance rules) is reliable.
"""
import os
from sgraal import SgraalClient

client = SgraalClient(api_key=os.environ["SGRAAL_API_KEY"])

# Agent's memory state
memory = [
    {"id": "market_data", "content": "EUR/USD at 1.0850, trending up", "type": "tool_state",
     "timestamp_age_days": 0, "source_trust": 0.98, "source_conflict": 0.02, "downstream_count": 5},
    {"id": "risk_model", "content": "VaR limit: $50K per position", "type": "semantic",
     "timestamp_age_days": 30, "source_trust": 0.85, "source_conflict": 0.1, "downstream_count": 10},
    {"id": "compliance", "content": "MiFID II: max 5x leverage for retail", "type": "policy",
     "timestamp_age_days": 90, "source_trust": 0.99, "source_conflict": 0.01, "downstream_count": 20},
]

# Preflight check before trading
result = client.preflight(memory, domain="fintech", action_type="irreversible")

print(f"Omega: {result.omega_mem_final}/100")
print(f"Action: {result.recommended_action}")
print(f"Assurance: {result.assurance_score}%")

if result.recommended_action == "BLOCK":
    print("BLOCKED — memory state unreliable for trading!")
    for repair in result.repair_plan:
        print(f"  Fix: {repair['action']} on {repair['entry_id']}")
elif result.recommended_action == "USE_MEMORY":
    print("Safe to trade — executing strategy...")
else:
    print(f"Caution: {result.recommended_action} — proceeding with monitoring")
