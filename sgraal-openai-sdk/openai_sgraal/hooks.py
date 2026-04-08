"""Preflight hook for OpenAI message history."""
import os
import requests as http_requests


def preflight_hook(
    messages: list,
    api_key: str = None,
    domain: str = "general",
    action_type: str = "reversible",
    base_url: str = "https://api.sgraal.com",
    only_use_memory: bool = True,
) -> list:
    """Filter OpenAI messages through Sgraal preflight.

    Converts messages to MemCube v2 format, runs preflight,
    and returns safe messages (or all annotated).
    """
    if not messages:
        return []

    key = api_key or os.environ.get("SGRAAL_API_KEY", "")
    if not key:
        return messages

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

    if not memory_state:
        return messages

    try:
        resp = http_requests.post(
            f"{base_url}/v1/preflight",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"memory_state": memory_state, "domain": domain, "action_type": action_type},
            timeout=10,
        )
        if not resp.ok:
            return messages
        data = resp.json()
    except Exception:
        return messages

    decision = data.get("recommended_action", "USE_MEMORY")
    omega = data.get("omega_mem_final", 0)

    annotated = [{**m, "sgraal_decision": decision, "sgraal_omega": omega} for m in messages]

    if only_use_memory and decision != "USE_MEMORY":
        return []
    return annotated
