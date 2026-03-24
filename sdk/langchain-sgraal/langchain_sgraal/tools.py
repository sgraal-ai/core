"""Sgraal Memory Guard tool for LangChain."""

from __future__ import annotations

import os
from typing import Any, Optional, Type

import requests
from pydantic import BaseModel, Field

try:
    from langchain_core.tools import BaseTool
except ImportError:
    from langchain.tools import BaseTool


class SgraalPreflightInput(BaseModel):
    """Input schema for SgraalMemoryGuard tool."""

    memory_state: list[dict[str, Any]] = Field(
        description="List of memory entries to check. Each entry needs: id, content, type, timestamp_age_days."
    )
    action_type: str = Field(
        default="reversible",
        description="How critical is the action? informational/reversible/irreversible/destructive",
    )
    domain: str = Field(
        default="general",
        description="Domain context: general/customer_support/coding/legal/fintech/medical",
    )


class SgraalMemoryGuard(BaseTool):
    """Check if AI agent memory is reliable before acting.

    Calls the Sgraal preflight API to score memory risk and returns
    USE_MEMORY (safe), WARN (proceed with caution), or BLOCK (stop).

    Example:
        from langchain_sgraal import SgraalMemoryGuard

        tool = SgraalMemoryGuard(api_key="sg_live_...")
        result = tool.invoke({
            "memory_state": [{
                "id": "mem_001",
                "content": "User prefers metric units",
                "type": "preference",
                "timestamp_age_days": 45,
            }],
            "action_type": "irreversible",
            "domain": "fintech",
        })
    """

    name: str = "sgraal_memory_guard"
    description: str = (
        "Check if AI agent memory is reliable before acting. "
        "Returns USE_MEMORY (safe), WARN (caution), or BLOCK (stop). "
        "Call this BEFORE making any decision based on stored memory."
    )
    args_schema: Type[BaseModel] = SgraalPreflightInput

    api_key: str = ""
    base_url: str = "https://api.sgraal.com"
    timeout: float = 10.0

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs: Any):
        super().__init__(**kwargs)
        self.api_key = api_key or os.environ.get("SGRAAL_API_KEY", "")
        if base_url:
            self.base_url = base_url

    def _run(
        self,
        memory_state: list[dict[str, Any]],
        action_type: str = "reversible",
        domain: str = "general",
    ) -> str:
        """Run the Sgraal preflight check."""
        if not self.api_key:
            return "ERROR: SGRAAL_API_KEY not set"

        try:
            resp = requests.post(
                f"{self.base_url}/v1/preflight",
                json={
                    "memory_state": memory_state,
                    "action_type": action_type,
                    "domain": domain,
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            action = data.get("recommended_action", "WARN")
            omega = data.get("omega_mem_final", 0)
            note = data.get("explainability_note", "")

            if action == "BLOCK":
                return f"BLOCKED (Ω={omega}): {note}. Do NOT proceed — memory is unreliable."
            elif action in ("WARN", "ASK_USER"):
                return f"WARNING (Ω={omega}): {note}. Proceed with caution."
            else:
                return f"SAFE (Ω={omega}): Memory is reliable. Proceed."

        except Exception as e:
            return f"SGRAAL_ERROR: {str(e)}"
