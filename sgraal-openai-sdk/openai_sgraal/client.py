"""OpenAI + Sgraal integrated client."""
import os

try:
    from sgraal import SgraalClient
except ImportError:
    SgraalClient = None


class MemoryUnsafeError(RuntimeError):
    """Raised when Sgraal blocks memory as unsafe."""
    pass


class OpenAISgraalClient:
    """OpenAI client with Sgraal preflight validation.

    Usage:
        client = OpenAISgraalClient(sgraal_api_key="sg_live_...")
        result = client.safe_complete(
            messages=[{"role": "user", "content": "What is my balance?"}],
            model="gpt-4o", domain="fintech"
        )
    """

    def __init__(self, sgraal_api_key: str, openai_api_key: str = None,
                 base_url: str = "https://api.sgraal.com"):
        if SgraalClient is None:
            raise ImportError("sgraal package required: pip install sgraal>=0.2.0")
        self.sgraal = SgraalClient(sgraal_api_key, base_url)
        self._openai_key = openai_api_key or os.environ.get("OPENAI_API_KEY", "")

    def safe_complete(self, messages: list, model: str = "gpt-4o",
                      domain: str = "general", action_type: str = "reversible",
                      **kwargs) -> dict:
        """Run Sgraal preflight then OpenAI completion.

        Raises MemoryUnsafeError if preflight returns BLOCK.
        """
        memory_state = [
            {
                "id": f"msg_{i}",
                "content": str(m.get("content", "")),
                "type": "episodic",
                "timestamp_age_days": 0,
                "source_trust": 0.85 if m.get("role") == "system" else 0.7,
                "source_conflict": 0.05,
                "downstream_count": 1,
            }
            for i, m in enumerate(messages)
            if isinstance(m, dict) and m.get("content")
        ]

        preflight = self.sgraal.preflight(
            memory_state=memory_state, domain=domain, action_type=action_type,
        )

        decision = preflight.get("recommended_action", "USE_MEMORY")
        omega = preflight.get("omega_mem_final", 0)

        if decision == "BLOCK":
            raise MemoryUnsafeError(
                f"Sgraal blocked: omega={omega}, reason={preflight.get('explainability_note', '')}"
            )

        # Call OpenAI
        try:
            import openai
            client = openai.OpenAI(api_key=self._openai_key) if self._openai_key else openai.OpenAI()
            completion = client.chat.completions.create(model=model, messages=messages, **kwargs)
            return {
                "completion": completion,
                "sgraal_decision": decision,
                "sgraal_omega": omega,
                "sgraal_preflight": preflight,
            }
        except ImportError:
            return {"error": "openai package not installed", "sgraal_decision": decision, "sgraal_omega": omega}
