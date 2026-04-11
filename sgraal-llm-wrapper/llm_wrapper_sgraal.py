"""sgraal-llm-wrapper: Drop-in wrapper that adds Sgraal preflight to any LLM call."""
from sgraal import SgraalClient


class SgraalLLMWrapper:
    """Drop-in wrapper for any LLM call. Adds Sgraal preflight validation."""

    def __init__(self, api_key: str, domain: str = "general", block_on_warn: bool = False):
        self.client = SgraalClient(api_key)
        self.domain = domain
        self.block_on_warn = block_on_warn

    def validate(self, context: list, action_type: str = "reversible") -> dict:
        if not context:
            return {"recommended_action": "USE_MEMORY", "skipped": True}
        memory_state = [
            {"id": f"llm_ctx_{i:03d}", "content": str(c)[:500], "type": "semantic",
             "timestamp_age_days": 0, "source_trust": 0.8, "source_conflict": 0.1, "downstream_count": 1}
            for i, c in enumerate(context, 1)
        ]
        return self.client.preflight(memory_state=memory_state, domain=self.domain, action_type=action_type)

    def wrap(self, llm_fn, action_type: str = "reversible"):
        """Returns a wrapped version of llm_fn that validates context first."""
        def wrapped(*args, context=None, **kwargs):
            if context:
                result = self.validate(context, action_type)
                decision = result.get("recommended_action", "BLOCK")
                if decision == "BLOCK" or (decision in ("WARN", "ASK_USER") and self.block_on_warn):
                    raise ValueError(
                        f"Sgraal preflight: {decision} — "
                        f"omega={result.get('omega_mem_final')}, "
                        f"attack_surface={result.get('attack_surface_level')}")
            return llm_fn(*args, **kwargs)
        return wrapped

    def decorator(self, action_type: str = "reversible"):
        """Use as decorator: @wrapper.decorator('irreversible')"""
        def decorate(fn):
            return self.wrap(fn, action_type)
        return decorate
