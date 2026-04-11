"""zep-sgraal: Sgraal preflight validation bridge for Zep memory store."""
from sgraal import SgraalClient


class ZepSgraal:
    def __init__(self, api_key: str, domain: str = "general"):
        self.client = SgraalClient(api_key)
        self.domain = domain

    def validate_search_results(self, results: list, action_type: str = "reversible") -> dict:
        memory_state = []
        for i, r in enumerate(results, 1):
            if hasattr(r, 'message'):
                content = getattr(r.message, 'content', str(r))
                score = getattr(r, 'dist', 0.85)
            elif isinstance(r, dict):
                content = r.get('message', {}).get('content', str(r)) if isinstance(r.get('message'), dict) else str(r.get('message', r))
                score = r.get('dist', 0.85)
            else:
                content, score = str(r), 0.85
            memory_state.append({"id": f"zep_result_{i:03d}", "content": content[:500], "type": "semantic",
                                 "timestamp_age_days": 0, "source_trust": min(float(score), 1.0),
                                 "source_conflict": 0.05, "downstream_count": 1})
        return self.client.preflight(memory_state=memory_state, domain=self.domain, action_type=action_type)

    def is_safe(self, results: list, action_type: str = "reversible") -> bool:
        result = self.validate_search_results(results, action_type)
        return result.get("recommended_action") in ("USE_MEMORY", "WARN")
