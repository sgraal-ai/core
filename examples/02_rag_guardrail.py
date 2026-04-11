"""RAG pipeline guardrail example.

Validates retrieved chunks before passing to LLM generation.
Run: pip install sgraal && python examples/02_rag_guardrail.py
"""
from sgraal import SgraalClient

client = SgraalClient("sg_demo_playground")

# Simulated RAG retrieval
retrieved_chunks = [
    "Revenue grew 12% YoY in Q4 2025, driven by enterprise expansion.",
    "EBITDA margin improved to 34%, up from 31% in the prior quarter.",
    "Net debt-to-equity ratio stands at 0.4, within target range.",
]

# Validate all chunks as a memory state
memory_state = [
    {"id": f"chunk_{i}", "content": chunk, "type": "semantic",
     "timestamp_age_days": 0, "source_trust": 0.85,
     "source_conflict": 0.05, "downstream_count": 1}
    for i, chunk in enumerate(retrieved_chunks, 1)
]

result = client.preflight(
    memory_state=memory_state,
    domain="fintech",
    action_type="informational"
)

decision = result["recommended_action"]
print(f"Decision: {decision}")

if decision in ("USE_MEMORY", "WARN"):
    print("Safe to generate — passing chunks to LLM")
    # llm.generate(context=retrieved_chunks, prompt="Summarize financials")
else:
    print(f"BLOCKED — {result.get('attack_surface_level', 'unknown')} risk")
    print(f"Flags: {result.get('active_detection_layers', [])}")
