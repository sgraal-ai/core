from __future__ import annotations

from typing import Any, Optional

from .client import SgraalClient

# Lazy stubs — replaced by real imports when available
genai = None
OpenAI = None

try:
    import google.generativeai as genai  # type: ignore[no-redef]
except ImportError:
    pass

try:
    from openai import OpenAI  # type: ignore[no-redef]
except ImportError:
    pass


class _BaseGuard:
    """Base class for LLM provider guards."""

    def __init__(self, sgraal_api_key: str, base_url: Optional[str] = None):
        self._sgraal = SgraalClient(api_key=sgraal_api_key, base_url=base_url)

    def _preflight(
        self,
        memory_data: list[dict[str, Any]],
        action_type: str = "irreversible",
        domain: str = "general",
    ):
        return self._sgraal.preflight(
            memory_state=memory_data,
            action_type=action_type,
            domain=domain,
        )


class GeminiGuard(_BaseGuard):
    """Sgraal memory governance guard for Google Gemini.

    Runs a preflight check before every Gemini call. Blocks on BLOCK,
    adds warning context on WARN/ASK_USER, passes through on USE_MEMORY.

    Usage:
        guard = GeminiGuard(sgraal_api_key="sg_live_...", gemini_api_key="...")
        response = guard.check_and_generate("What is the user's address?", memory_data=[...])
    """

    def __init__(
        self,
        sgraal_api_key: str,
        gemini_api_key: str,
        model: str = "gemini-1.5-flash",
        sgraal_base_url: Optional[str] = None,
    ):
        super().__init__(sgraal_api_key, sgraal_base_url)
        self._gemini_api_key = gemini_api_key
        self._model = model

    def check_and_generate(
        self,
        query: str,
        memory_data: list[dict[str, Any]],
        action_type: str = "irreversible",
        domain: str = "general",
    ) -> str:
        """Run preflight, then generate with Gemini if safe.

        Returns the Gemini response string, or a block/warning message.
        """
        result = self._preflight(memory_data, action_type, domain)

        if result.recommended_action == "BLOCK":
            return (
                f"[SGRAAL BLOCKED] Memory governance check failed "
                f"(Ω={result.omega_mem_final}). {result.explainability_note} "
                f"Resolve memory issues before proceeding."
            )

        warning_prefix = ""
        if result.recommended_action in ("WARN", "ASK_USER"):
            warning_prefix = (
                f"[SGRAAL WARNING: Ω={result.omega_mem_final}, "
                f"{result.explainability_note}] "
            )

        if genai is None:
            raise ImportError("google-generativeai package required: pip install google-generativeai")

        genai.configure(api_key=self._gemini_api_key)
        model = genai.GenerativeModel(self._model)
        response = model.generate_content(f"{warning_prefix}{query}")
        return response.text


class OpenAIGuard(_BaseGuard):
    """Sgraal memory governance guard for OpenAI GPT models.

    Runs a preflight check before every OpenAI call. Blocks on BLOCK,
    adds warning context on WARN/ASK_USER, passes through on USE_MEMORY.

    Usage:
        guard = OpenAIGuard(sgraal_api_key="sg_live_...", openai_api_key="...")
        response = guard.check_and_generate("Summarize the contract", memory_data=[...])
    """

    def __init__(
        self,
        sgraal_api_key: str,
        openai_api_key: str,
        model: str = "gpt-4",
        sgraal_base_url: Optional[str] = None,
    ):
        super().__init__(sgraal_api_key, sgraal_base_url)
        self._openai_api_key = openai_api_key
        self._model = model

    def check_and_generate(
        self,
        query: str,
        memory_data: list[dict[str, Any]],
        action_type: str = "irreversible",
        domain: str = "general",
    ) -> str:
        """Run preflight, then generate with OpenAI if safe.

        Returns the OpenAI response string, or a block/warning message.
        """
        result = self._preflight(memory_data, action_type, domain)

        if result.recommended_action == "BLOCK":
            return (
                f"[SGRAAL BLOCKED] Memory governance check failed "
                f"(Ω={result.omega_mem_final}). {result.explainability_note} "
                f"Resolve memory issues before proceeding."
            )

        warning_prefix = ""
        if result.recommended_action in ("WARN", "ASK_USER"):
            warning_prefix = (
                f"[SGRAAL WARNING: Ω={result.omega_mem_final}, "
                f"{result.explainability_note}] "
            )

        if OpenAI is None:
            raise ImportError("openai package required: pip install openai")

        client = OpenAI(api_key=self._openai_api_key)
        response = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": f"{warning_prefix}{query}"}],
        )
        return response.choices[0].message.content
