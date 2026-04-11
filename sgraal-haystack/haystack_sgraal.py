"""haystack-sgraal: Sgraal preflight validation bridge for Haystack (deepset)."""
from sgraal import SgraalClient


class HaystackSgraal:
    def __init__(self, api_key: str, domain: str = "general"):
        self.client = SgraalClient(api_key)
        self.domain = domain

    def validate_documents(self, documents: list, action_type: str = "informational") -> dict:
        memory_state = []
        for i, doc in enumerate(documents, 1):
            if hasattr(doc, 'content'):
                content = doc.content or ""
            elif isinstance(doc, dict):
                content = doc.get('content', str(doc))
            else:
                content = str(doc)
            memory_state.append({
                "id": f"haystack_doc_{i:03d}", "content": content[:500],
                "type": "semantic", "timestamp_age_days": 0,
                "source_trust": 0.83, "source_conflict": 0.07, "downstream_count": 1
            })
        return self.client.preflight(memory_state=memory_state, domain=self.domain, action_type=action_type)

    def filter_safe_documents(self, documents: list, action_type: str = "informational") -> list:
        if not documents:
            return []
        result = self.validate_documents(documents, action_type)
        return documents if result.get("recommended_action") in ("USE_MEMORY", "WARN") else []

    def is_safe(self, documents: list, action_type: str = "informational") -> bool:
        result = self.validate_documents(documents, action_type)
        return result.get("recommended_action") in ("USE_MEMORY", "WARN")
