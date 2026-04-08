"""LangChain integration example — validate memory before recall."""
import os
from sgraal import SgraalClient

client = SgraalClient(
    api_key=os.environ.get("SGRAAL_API_KEY", "sg_demo_playground")
)


def safe_recall(memory_entries: list, query: str) -> str:
    """Validate memory with Sgraal before returning to LangChain."""
    memory_state = [
        {
            "id": f"mem_{i}",
            "content": entry,
            "type": "semantic",
            "timestamp_age_days": 1,
            "source_trust": 0.9,
            "source_conflict": 0.05,
            "downstream_count": 2,
        }
        for i, entry in enumerate(memory_entries)
    ]

    result = client.preflight(
        memory_state=memory_state,
        domain="general",
        action_type="reversible",
    )

    if result["recommended_action"] == "BLOCK":
        return "[Memory blocked by Sgraal — unsafe to recall]"

    if result["recommended_action"] == "WARN":
        print(f"Warning: omega={result['omega_mem_final']}")

    return query


# Example usage
memories = [
    "User prefers email notifications",
    "Last login: 2025-12-01",
]
answer = safe_recall(memories, "What are the user's preferences?")
print(f"Answer: {answer}")
