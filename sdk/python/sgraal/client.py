from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass
from typing import Any, Literal, Optional

import requests


@dataclass(frozen=True)
class PreflightResult:
    omega_mem_final: float
    recommended_action: Literal["USE_MEMORY", "WARN", "ASK_USER", "BLOCK"]
    assurance_score: float
    explainability_note: str
    component_breakdown: dict[str, float]
    fallback: bool = False
    circuit_state: str = "CLOSED"


class CircuitBreaker:
    """Client-side circuit breaker for API calls."""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 30):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._state = "CLOSED"
        self._last_failure_time: float = 0

    @property
    def state(self) -> str:
        if self._state == "OPEN":
            if time.monotonic() - self._last_failure_time >= self._recovery_timeout:
                self._state = "HALF_OPEN"
        return self._state

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._failure_threshold:
            self._state = "OPEN"

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = "CLOSED"

    def should_allow(self) -> bool:
        s = self.state
        return s in ("CLOSED", "HALF_OPEN")

    def reset(self) -> None:
        self._failure_count = 0
        self._state = "CLOSED"
        self._last_failure_time = 0


# Weibull constants for local fallback scoring
_WEIBULL_LAMBDA = {
    "tool_state": 0.15, "shared_workflow": 0.08, "episodic": 0.05,
    "preference": 0.03, "semantic": 0.01, "policy": 0.005, "identity": 0.002,
}
_WEIBULL_DEFAULT = 0.05


def _local_score(entries: list[dict[str, Any]]) -> float:
    """Lightweight Weibull-only scoring for fallback."""
    if not entries:
        return 0.0
    total = 0.0
    for e in entries:
        age = e.get("timestamp_age_days", 0)
        mtype = e.get("type", "semantic")
        lam = _WEIBULL_LAMBDA.get(mtype, _WEIBULL_DEFAULT)
        decay = 1.0 - math.exp(-((age * lam) ** 1.0))
        total += min(100.0, decay * 100.0)
    return round(total / len(entries), 1)


class SgraalClient:
    """Client for the Sgraal memory governance API.

    Supports graceful fallback with circuit breaker when API is unavailable.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        fallback_policy: str = "warn",
        timeout: float = 10.0,
        failure_threshold: int = 3,
        recovery_timeout: int = 30,
    ):
        self.api_key = api_key or os.environ.get("SGRAAL_API_KEY", "")
        self.base_url = (
            base_url or os.environ.get("SGRAAL_API_URL", "https://api.sgraal.com")
        ).rstrip("/")
        self.fallback_policy = fallback_policy
        self.timeout = timeout
        self.circuit = CircuitBreaker(failure_threshold, recovery_timeout)

        if not self.api_key:
            raise ValueError(
                "Sgraal API key required. Pass api_key or set SGRAAL_API_KEY."
            )

    def _fallback_result(self, entries: list[dict[str, Any]]) -> PreflightResult:
        omega = _local_score(entries)
        if self.fallback_policy == "block":
            action: Literal["USE_MEMORY", "WARN", "BLOCK"] = "BLOCK"
        elif self.fallback_policy == "warn":
            action = "WARN"
        else:
            action = "USE_MEMORY"
        return PreflightResult(
            omega_mem_final=omega,
            recommended_action=action,
            assurance_score=0,
            explainability_note="API_UNAVAILABLE — fallback scoring only.",
            component_breakdown={},
            fallback=True,
            circuit_state=self.circuit.state,
        )

    def preflight(
        self,
        memory_state: list[dict[str, Any]],
        action_type: str = "reversible",
        domain: str = "general",
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> PreflightResult:
        """Run a preflight check on memory state before acting.

        If the API is unavailable and circuit is open, returns a fallback
        result based on fallback_policy (allow/warn/block).
        """
        # Circuit breaker: fail fast if open
        if not self.circuit.should_allow():
            return self._fallback_result(memory_state)

        payload: dict[str, Any] = {
            "memory_state": memory_state,
            "action_type": action_type,
            "domain": domain,
        }
        if agent_id is not None:
            payload["agent_id"] = agent_id
        if task_id is not None:
            payload["task_id"] = task_id

        try:
            resp = requests.post(
                f"{self.base_url}/v1/preflight",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            self.circuit.record_success()

            return PreflightResult(
                omega_mem_final=data["omega_mem_final"],
                recommended_action=data["recommended_action"],
                assurance_score=data["assurance_score"],
                explainability_note=data["explainability_note"],
                component_breakdown=data["component_breakdown"],
                fallback=False,
                circuit_state=self.circuit.state,
            )
        except Exception:
            self.circuit.record_failure()
            return self._fallback_result(memory_state)

    def signup(self, email: str) -> dict[str, Any]:
        """Sign up for a Sgraal API key."""
        resp = requests.post(
            f"{self.base_url}/v1/signup",
            json={"email": email},
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()
