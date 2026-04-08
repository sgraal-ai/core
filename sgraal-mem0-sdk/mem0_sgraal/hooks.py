"""Standalone preflight hook for mem0 memories — no mem0ai dependency required."""
import os
import requests


def preflight_hook(
    memories: list,
    domain: str = "general",
    action_type: str = "reversible",
    api_key: str = None,
    base_url: str = "https://api.sgraal.com",
    only_use_memory: bool = True,
) -> list:
    """Annotate mem0 memories with Sgraal preflight decisions.

    Each memory dict gets ``sgraal_decision`` and ``sgraal_omega`` fields.

    Args:
        memories: List of mem0 memory dicts (must have ``id`` and ``memory`` or ``content``).
        domain: Sgraal domain (general, fintech, medical, legal, coding).
        action_type: reversible, irreversible, or destructive.
        api_key: Sgraal API key. Falls back to ``SGRAAL_API_KEY`` env var.
        base_url: Sgraal API base URL.
        only_use_memory: If True, return only USE_MEMORY memories.
            If False, return all memories with decision annotations.

    Returns:
        List of memory dicts, each annotated with ``sgraal_decision`` and ``sgraal_omega``.
        On API failure, returns all memories unchanged (graceful degradation).
    """
    if not memories:
        return []

    key = api_key or os.environ.get("SGRAAL_API_KEY", "")
    if not key:
        return memories

    memory_state = []
    for m in memories:
        memory_state.append({
            "id": str(m.get("id", "")),
            "content": str(m.get("memory", m.get("content", ""))),
            "type": "semantic",
            "timestamp_age_days": float(m.get("age_days", 1)),
            "source_trust": float(m.get("score", m.get("source_trust", 0.8))),
            "source_conflict": float(m.get("source_conflict", 0.1)),
            "downstream_count": int(m.get("downstream_count", 1)),
        })

    try:
        resp = requests.post(
            f"{base_url}/v1/preflight",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"memory_state": memory_state, "domain": domain, "action_type": action_type},
            timeout=10,
        )
        if not resp.ok:
            return memories
        data = resp.json()
    except Exception:
        return memories

    decision = data.get("recommended_action", "USE_MEMORY")
    omega = data.get("omega_mem_final", 0)

    annotated = []
    for m in memories:
        enriched = {**m, "sgraal_decision": decision, "sgraal_omega": omega}
        annotated.append(enriched)

    if only_use_memory:
        return [m for m in annotated if m.get("sgraal_decision") == "USE_MEMORY"]

    return annotated
