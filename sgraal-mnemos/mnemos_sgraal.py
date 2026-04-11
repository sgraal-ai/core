"""
mnemos-sgraal: Sgraal preflight validation bridge for mnemos memory engine.
Validates mnemos memories before agent action.
"""
from sgraal import SgraalClient


class MnemosSgraal:
    def __init__(self, api_key: str, domain: str = "general"):
        self.client = SgraalClient(api_key)
        self.domain = domain

    def validate_memory(self, memory_content: str, action_type: str = "reversible",
                       source_trust: float = 0.8, downstream_count: int = 1) -> dict:
        """
        Validate a mnemos memory entry before acting on it.

        Args:
            memory_content: The memory text from mnemos
            action_type: informational|reversible|irreversible|destructive
            source_trust: Trust score for this memory source (0.0-1.0)
            downstream_count: Number of agents that will use this memory

        Returns:
            Sgraal preflight response dict
        """
        memory_state = [{
            "id": "mnemos_memory_001",
            "content": memory_content,
            "type": "semantic",
            "timestamp_age_days": 0,
            "source_trust": source_trust,
            "source_conflict": 0.1,
            "downstream_count": downstream_count
        }]
        return self.client.preflight(
            memory_state=memory_state,
            domain=self.domain,
            action_type=action_type
        )

    def validate_memories(self, memories: list, action_type: str = "reversible",
                         source_trust: float = 0.8) -> dict:
        """Validate multiple mnemos memories as a batch."""
        memory_state = [
            {
                "id": f"mnemos_memory_{i:03d}",
                "content": m,
                "type": "semantic",
                "timestamp_age_days": 0,
                "source_trust": source_trust,
                "source_conflict": 0.05,
                "downstream_count": 1
            }
            for i, m in enumerate(memories, 1)
        ]
        return self.client.preflight(
            memory_state=memory_state,
            domain=self.domain,
            action_type=action_type
        )

    def is_safe(self, memory_content: str, action_type: str = "reversible") -> bool:
        """Simple boolean check — True if USE_MEMORY, False otherwise."""
        result = self.validate_memory(memory_content, action_type)
        return result.get("recommended_action") == "USE_MEMORY"
