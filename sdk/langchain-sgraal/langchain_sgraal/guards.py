"""Sgraal guards for LangGraph nodes."""

from __future__ import annotations

import functools
import os
from typing import Any, Callable, Optional

import requests


class SgraalBlockedError(Exception):
    """Raised when Sgraal blocks execution due to unreliable memory."""

    def __init__(self, omega: float, note: str):
        self.omega = omega
        self.note = note
        super().__init__(f"Sgraal BLOCKED (Ω={omega}): {note}")


def _call_preflight(
    memory_state: list[dict[str, Any]],
    action_type: str = "reversible",
    domain: str = "general",
    api_key: Optional[str] = None,
    base_url: str = "https://api.sgraal.com",
) -> dict[str, Any]:
    """Call the Sgraal preflight API."""
    key = api_key or os.environ.get("SGRAAL_API_KEY", "")
    resp = requests.post(
        f"{base_url}/v1/preflight",
        json={
            "memory_state": memory_state,
            "action_type": action_type,
            "domain": domain,
        },
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def sgraal_guard(
    memory_state: list[dict[str, Any]] | Callable[..., list[dict[str, Any]]],
    action_type: str = "reversible",
    domain: str = "general",
    block_on: str = "BLOCK",
    api_key: Optional[str] = None,
) -> Callable:
    """Decorator that runs a Sgraal preflight check before a LangGraph node.

    Args:
        memory_state: static list of MemCube dicts, or callable that returns them
        action_type: informational/reversible/irreversible/destructive
        domain: general/customer_support/coding/legal/fintech/medical
        block_on: "BLOCK" (default), "ASK_USER", or "WARN"
        api_key: optional API key (defaults to SGRAAL_API_KEY env var)

    Example:
        @sgraal_guard(
            memory_state=lambda state: state["memories"],
            action_type="irreversible",
            domain="fintech",
            block_on="BLOCK",
        )
        def process_trade(state):
            return {"result": execute_trade(state)}
    """
    block_levels = {
        "BLOCK": {"BLOCK"},
        "ASK_USER": {"BLOCK", "ASK_USER"},
        "WARN": {"BLOCK", "ASK_USER", "WARN"},
    }
    blocked = block_levels.get(block_on, {"BLOCK"})

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            entries = (
                memory_state(*args, **kwargs)
                if callable(memory_state)
                else memory_state
            )

            try:
                data = _call_preflight(entries, action_type, domain, api_key)
                action = data.get("recommended_action", "WARN")

                if action in blocked:
                    raise SgraalBlockedError(
                        data.get("omega_mem_final", 0),
                        data.get("explainability_note", ""),
                    )
            except SgraalBlockedError:
                raise
            except Exception:
                pass  # graceful degradation: allow if API fails

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def with_preflight(
    fn: Callable,
    get_memory: Callable[..., list[dict[str, Any]]],
    action_type: str = "reversible",
    domain: str = "general",
    api_key: Optional[str] = None,
) -> Callable:
    """Wrap a LangGraph node with Sgraal preflight check.

    Args:
        fn: the node function to wrap
        get_memory: callable that extracts memory entries from the node's args
        action_type: informational/reversible/irreversible/destructive
        domain: general/customer_support/coding/legal/fintech/medical
        api_key: optional API key

    Example:
        def trade_node(state):
            return execute_trade(state)

        safe_trade = with_preflight(
            trade_node,
            get_memory=lambda state: state["memories"],
            action_type="irreversible",
            domain="fintech",
        )
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        entries = get_memory(*args, **kwargs)

        try:
            data = _call_preflight(entries, action_type, domain, api_key)
            action = data.get("recommended_action", "WARN")

            if action == "BLOCK":
                raise SgraalBlockedError(
                    data.get("omega_mem_final", 0),
                    data.get("explainability_note", ""),
                )
        except SgraalBlockedError:
            raise
        except Exception:
            pass

        return fn(*args, **kwargs)

    return wrapper
