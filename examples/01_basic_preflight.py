"""Basic preflight validation example.

Run: pip install sgraal && python examples/01_basic_preflight.py
"""
from sgraal import SgraalClient

client = SgraalClient("sg_demo_playground")

result = client.preflight(
    memory_state=[{
        "id": "mem_001",
        "content": "Customer prefers email communication for all updates.",
        "type": "preference",
        "timestamp_age_days": 5,
        "source_trust": 0.9,
        "source_conflict": 0.05,
        "downstream_count": 1
    }],
    domain="general",
    action_type="reversible"
)

print(f"Decision: {result['recommended_action']}")
print(f"Omega:    {result['omega_mem_final']}")
print(f"Natural:  {result.get('naturalness_level', 'N/A')}")
print(f"Attack:   {result.get('attack_surface_level', 'N/A')}")
