"""Multi-agent memory validation with provenance chain.

Demonstrates BLOCK on circular reference in provenance chain.
Run: pip install sgraal && python examples/03_multi_agent_chain.py
"""
from sgraal import SgraalClient

client = SgraalClient("sg_demo_playground")

# Agent A produced a memory, passed to Agent B, which passed back to Agent A
# This creates a circular provenance chain
memory_with_loop = [{
    "id": "chain_mem_001",
    "content": "Trade execution approved for portfolio rebalancing.",
    "type": "semantic",
    "timestamp_age_days": 0.5,
    "source_trust": 0.91,
    "source_conflict": 0.03,
    "downstream_count": 5,
    "provenance_chain": ["agent-planner", "agent-executor", "agent-planner"]
}]

result = client.preflight(
    memory_state=memory_with_loop,
    domain="fintech",
    action_type="irreversible"
)

print(f"Decision:   {result['recommended_action']}")
print(f"Provenance: {result.get('provenance_chain_integrity', 'N/A')}")
print(f"Flags:      {result.get('provenance_chain_flags', [])}")
print(f"Chain depth:{result.get('chain_depth', 0)}")

if result["recommended_action"] == "BLOCK":
    print("\nCircular reference detected — memory looped back through same agent.")
    print("Repair: Verify provenance chain integrity before trusting.")
