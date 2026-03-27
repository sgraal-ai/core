"""Sgraal guard for OpenAI Agents SDK — preflight on tool calls."""
from __future__ import annotations
import logging
import warnings
from typing import Optional

logger = logging.getLogger(__name__)


class SgraalBlockedError(Exception):
    """Raised when preflight returns BLOCK and on_block='raise'."""
    pass


class SgraalGuard:
    """OpenAI Agents SDK hook — runs Sgraal preflight before tool execution.

    Usage:
        guard = SgraalGuard(api_key="sg_live_...", on_block="raise")
        guard.on_tool_start(tool_name, tool_input)
    """

    def __init__(self, api_key: str, api_url: str = "https://api.sgraal.com", on_block: str = "raise"):
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.on_block = on_block

    def _extract_memory_state(self, tool_input: dict) -> Optional[list]:
        """Extract memory_state from tool input. Returns None if not found."""
        if not isinstance(tool_input, dict):
            return None
        return tool_input.get("memory_state")

    def _run_preflight(self, memory_state: list) -> dict:
        import requests
        resp = requests.post(f"{self.api_url}/v1/preflight",
            json={"memory_state": memory_state},
            headers={"Authorization": f"Bearer {self.api_key}"}, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def on_tool_start(self, tool_name: str, tool_input: dict) -> Optional[dict]:
        """Called before tool execution. Returns preflight result or None."""
        memory_state = self._extract_memory_state(tool_input)
        if memory_state is None:
            return None  # No memory_state → skip silently

        try:
            result = self._run_preflight(memory_state)
        except Exception as e:
            logger.warning("Sgraal preflight failed for tool %s: %s", tool_name, e)
            return None

        action = result.get("recommended_action", "USE_MEMORY")
        if action == "BLOCK":
            if self.on_block == "raise":
                raise SgraalBlockedError(f"Sgraal BLOCK on tool {tool_name}: omega={result.get('omega_mem_final')}")
            elif self.on_block == "warn":
                warnings.warn(f"Sgraal BLOCK on tool {tool_name}", UserWarning, stacklevel=2)
            elif self.on_block == "skip":
                return result
        elif action == "WARN":
            warnings.warn(f"Sgraal WARN on tool {tool_name}: omega={result.get('omega_mem_final')}", UserWarning, stacklevel=2)

        return result
