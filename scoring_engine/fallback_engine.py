from __future__ import annotations

import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from .omega_mem import MemoryEntry, WEIBULL_LAMBDA, WEIBULL_LAMBDA_DEFAULT, WEIBULL_K


class FallbackPolicy(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class FallbackResult:
    omega_mem_final: float
    recommended_action: Literal["USE_MEMORY", "WARN", "BLOCK"]
    fallback: bool
    reason: str
    circuit_state: str


class CircuitBreaker:
    """Circuit breaker for API calls.

    CLOSED → normal operation, requests go through
    OPEN → all requests fail-fast with fallback (after failure_threshold consecutive failures)
    HALF_OPEN → one test request allowed (after recovery_timeout seconds)
    """

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 30):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._last_failure_time: float = 0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self._recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def should_allow_request(self) -> bool:
        s = self.state
        if s == CircuitState.CLOSED:
            return True
        if s == CircuitState.HALF_OPEN:
            return True  # allow one test request
        return False  # OPEN

    def reset(self) -> None:
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._last_failure_time = 0


class LocalFallbackScorer:
    """Lightweight Weibull-only scoring — no API call needed.

    Provides a best-effort freshness score when the API is unavailable.
    """

    @staticmethod
    def score(entry: MemoryEntry) -> float:
        """Score a single entry using Weibull decay only (0–100)."""
        lam = WEIBULL_LAMBDA.get(entry.type, WEIBULL_LAMBDA_DEFAULT)
        decay = 1.0 - math.exp(-((entry.timestamp_age_days * lam) ** WEIBULL_K))
        return round(min(100.0, decay * 100.0), 1)


class FallbackEngine:
    """Combines circuit breaker + local scorer + policy for graceful degradation."""

    def __init__(
        self,
        policy: FallbackPolicy = FallbackPolicy.WARN,
        failure_threshold: int = 3,
        recovery_timeout: int = 30,
    ):
        self.policy = policy
        self.circuit = CircuitBreaker(failure_threshold, recovery_timeout)
        self._scorer = LocalFallbackScorer()

    def get_fallback_result(self, entries: list[MemoryEntry]) -> FallbackResult:
        """Generate a fallback result when API is unavailable."""
        if not entries:
            omega = 0.0
        else:
            omega = round(sum(self._scorer.score(e) for e in entries) / len(entries), 1)

        if self.policy == FallbackPolicy.BLOCK:
            action: Literal["USE_MEMORY", "WARN", "BLOCK"] = "BLOCK"
        elif self.policy == FallbackPolicy.WARN:
            action = "WARN"
        else:
            action = "USE_MEMORY"

        return FallbackResult(
            omega_mem_final=omega,
            recommended_action=action,
            fallback=True,
            reason="API_UNAVAILABLE",
            circuit_state=self.circuit.state.value,
        )
