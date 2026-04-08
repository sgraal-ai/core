"""Hallucination detection example — catch fabricated memory entries."""
import os
from sgraal import SgraalClient

client = SgraalClient(
    api_key=os.environ.get("SGRAAL_API_KEY", "sg_demo_playground")
)

# Scenario: Agent claims verified data that was never actually verified
suspicious_memory = [
    {
        "id": "hal_001",
        "content": "Account balance verified: $127,450 (certified by compliance)",
        "type": "tool_state",
        "timestamp_age_days": 1,
        "source_trust": 0.95,  # Looks credible
        "source_conflict": 0.02,  # No contradiction
        "downstream_count": 1,
    }
]

result = client.preflight(
    memory_state=suspicious_memory,
    domain="fintech",
    action_type="irreversible",
)

print(f"Decision: {result['recommended_action']}")
print(f"Omega: {result['omega_mem_final']}")

# Check for hallucination indicators
if result.get("homology_torsion", {}).get("hallucination_risk"):
    print("Topological anomaly detected — possible hallucination")

if result.get("mahalanobis_analysis", {}).get("anomaly_count", 0) > 0:
    print("Statistical outlier detected")

# The omega score alone may not catch confident fabrication —
# structural metadata looks clean. Use multi-entry cross-validation
# and the /v1/cross-agent-check endpoint for deeper detection.
