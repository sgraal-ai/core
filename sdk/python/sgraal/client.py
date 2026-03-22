from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

import requests


@dataclass(frozen=True)
class PreflightResult:
    omega_mem_final: float
    recommended_action: Literal["USE_MEMORY", "WARN", "ASK_USER", "BLOCK"]
    assurance_score: float
    explainability_note: str
    component_breakdown: dict[str, float]


class SgraalClient:
    """Client for the Sgraal memory governance API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.api_key = api_key or os.environ.get("SGRAAL_API_KEY", "")
        self.base_url = (
            base_url or os.environ.get("SGRAAL_API_URL", "https://api.sgraal.com")
        ).rstrip("/")

        if not self.api_key:
            raise ValueError(
                "Sgraal API key required. Pass api_key or set SGRAAL_API_KEY."
            )

    def preflight(
        self,
        memory_state: list[dict[str, Any]],
        action_type: str = "reversible",
        domain: str = "general",
        agent_id: str | None = None,
        task_id: str | None = None,
    ) -> PreflightResult:
        """Run a preflight check on memory state before acting.

        Args:
            memory_state: List of MemCube dicts with id, content, type,
                timestamp_age_days, source_trust, source_conflict, downstream_count.
            action_type: One of informational, reversible, irreversible, destructive.
            domain: One of general, customer_support, coding, legal, fintech, medical.
            agent_id: Optional agent identifier.
            task_id: Optional task identifier.

        Returns:
            PreflightResult with omega_mem_final, recommended_action,
            assurance_score, explainability_note, and component_breakdown.

        Raises:
            requests.HTTPError: If the API returns an error status.
        """
        payload: dict[str, Any] = {
            "memory_state": memory_state,
            "action_type": action_type,
            "domain": domain,
        }
        if agent_id is not None:
            payload["agent_id"] = agent_id
        if task_id is not None:
            payload["task_id"] = task_id

        resp = requests.post(
            f"{self.base_url}/v1/preflight",
            json=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        return PreflightResult(
            omega_mem_final=data["omega_mem_final"],
            recommended_action=data["recommended_action"],
            assurance_score=data["assurance_score"],
            explainability_note=data["explainability_note"],
            component_breakdown=data["component_breakdown"],
        )

    def signup(self, email: str) -> dict[str, Any]:
        """Sign up for a Sgraal API key.

        Args:
            email: Email address for the account.

        Returns:
            Dict with api_key, customer_id, and tier.

        Raises:
            requests.HTTPError: If the API returns an error status.
        """
        resp = requests.post(
            f"{self.base_url}/v1/signup",
            json={"email": email},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
