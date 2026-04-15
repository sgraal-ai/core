from __future__ import annotations

import functools
import logging
from typing import Any, Callable

from .client import SgraalClient

logger = logging.getLogger("sgraal")


class SgraalBlockedError(Exception):
    """Raised when Sgraal blocks execution due to unreliable memory."""

    def __init__(self, result: Any):
        self.result = result
        super().__init__(
            f"Sgraal BLOCKED (Ω={result['omega_mem_final']}): "
            f"{result.get('explainability_note', result.get('block_explanation', ''))}"
        )


def guard(
    memory_state: list[dict[str, Any]] | Callable[..., list[dict[str, Any]]],
    action_type: str = "reversible",
    domain: str = "general",
    block_on: str = "BLOCK",
    client: SgraalClient | None = None,
    fallback_policy: str = "warn",
) -> Callable:
    """Decorator that runs a Sgraal preflight check before function execution.

    Args:
        memory_state: Static list of MemCube dicts, or a callable that receives
            the same args as the wrapped function and returns memory entries.
        action_type: One of informational, reversible, irreversible, destructive.
        domain: One of general, customer_support, coding, legal, fintech, medical.
        block_on: Action level that triggers blocking. "BLOCK" blocks only on
            BLOCK. "ASK_USER" blocks on BLOCK and ASK_USER. "WARN" blocks on
            BLOCK, ASK_USER, and WARN.
        client: Optional SgraalClient instance. Defaults to a new client using
            SGRAAL_API_KEY env var.

    Usage:
        @guard(memory_state=[...], block_on="BLOCK")
        def send_invoice(customer_id):
            ...

        @guard(memory_state=lambda cid: fetch_memories(cid), block_on="WARN")
        def send_invoice(customer_id):
            ...
    """
    block_levels: dict[str, set[str]] = {
        "BLOCK": {"BLOCK"},
        "ASK_USER": {"BLOCK", "ASK_USER"},
        "WARN": {"BLOCK", "ASK_USER", "WARN"},
    }
    blocked_actions = block_levels.get(block_on, {"BLOCK"})

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            sgraal = client or SgraalClient(fallback_policy=fallback_policy)

            entries = (
                memory_state(*args, **kwargs)
                if callable(memory_state)
                else memory_state
            )

            result = sgraal.preflight(
                memory_state=entries,
                action_type=action_type,
                domain=domain,
            )

            if result["recommended_action"] in blocked_actions:
                raise SgraalBlockedError(result)

            if result["recommended_action"] in ("WARN", "ASK_USER"):
                logger.warning(
                    "Sgraal %s (Ω=%s): %s",
                    result["recommended_action"],
                    result["omega_mem_final"],
                    result.get("explainability_note", result.get("block_explanation", "")),
                )

            return fn(*args, **kwargs)

        return wrapper

    return decorator
