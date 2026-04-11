"""letta-sgraal: Sgraal preflight validation bridge for Letta (MemGPT) agent memory."""
from sgraal import SgraalClient


class LettaSgraal:
    def __init__(self, api_key: str, domain: str = "general"):
        self.client = SgraalClient(api_key)
        self.domain = domain

    def validate_memory_blocks(self, blocks, action_type: str = "reversible") -> dict:
        if isinstance(blocks, dict):
            blocks = [blocks]
        memory_state = [
            {"id": f"letta_block_{i:03d}",
             "content": str(b.get('value', b))[:500] if isinstance(b, dict) else str(b)[:500],
             "type": "semantic", "timestamp_age_days": 0, "source_trust": 0.83,
             "source_conflict": 0.07, "downstream_count": 1}
            for i, b in enumerate(blocks, 1)
        ]
        return self.client.preflight(memory_state=memory_state, domain=self.domain, action_type=action_type)

    def is_safe(self, blocks, action_type: str = "reversible") -> bool:
        result = self.validate_memory_blocks(blocks, action_type)
        return result.get("recommended_action") in ("USE_MEMORY", "WARN")
