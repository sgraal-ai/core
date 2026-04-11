"""
memvid-sgraal: Sgraal preflight validation bridge for Memvid memory layer.
Validates Memvid retrieved chunks before passing to LLM.
"""
from sgraal import SgraalClient


class MemvidSgraal:
    def __init__(self, api_key: str, domain: str = "general"):
        self.client = SgraalClient(api_key)
        self.domain = domain

    def validate_chunks(self, chunks: list, action_type: str = "informational",
                       source_trust: float = 0.85) -> dict:
        """
        Validate Memvid retrieved chunks before passing to LLM.

        Args:
            chunks: List of text chunks retrieved from Memvid
            action_type: informational|reversible|irreversible|destructive
            source_trust: Base trust score for Memvid source

        Returns:
            Sgraal preflight response dict
        """
        memory_state = [
            {
                "id": f"memvid_chunk_{i:03d}",
                "content": chunk,
                "type": "semantic",
                "timestamp_age_days": 0,
                "source_trust": source_trust,
                "source_conflict": 0.05,
                "downstream_count": 1
            }
            for i, chunk in enumerate(chunks, 1)
        ]
        return self.client.preflight(
            memory_state=memory_state,
            domain=self.domain,
            action_type=action_type
        )

    def filter_safe_chunks(self, chunks: list, action_type: str = "informational") -> list:
        """
        Filter chunks — return only those that pass preflight.
        Validates all chunks as a batch, returns list of safe chunks.
        """
        if not chunks:
            return []
        result = self.validate_chunks(chunks, action_type)
        if result.get("recommended_action") in ("USE_MEMORY", "WARN"):
            return chunks
        return []

    def validate_and_chat(self, chunks: list, query: str,
                         action_type: str = "informational") -> dict:
        """
        Validate chunks and return structured response for LLM consumption.

        Returns:
            {
                "safe_to_use": bool,
                "decision": str,
                "chunks": list[str],  # empty if BLOCK
                "sgraal_response": dict
            }
        """
        result = self.validate_chunks(chunks, action_type)
        decision = result.get("recommended_action", "BLOCK")
        safe = decision in ("USE_MEMORY", "WARN")
        return {
            "safe_to_use": safe,
            "decision": decision,
            "chunks": chunks if safe else [],
            "sgraal_response": result
        }
