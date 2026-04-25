"""Server-side derivation of self-authorship for memory entries.

Determines whether an entry was likely written by the current agent
(self-authored) vs received from an external source. Server-computed
from provenance metadata — NOT trusted from client input.

Used by Phase 2 detection adaptation to suppress SUSPICIOUS escalation
on self-authored stale entries. Phase 1.5: derivation only, no detection change.
"""
from __future__ import annotations

from typing import Optional


# Source types that indicate external origin
_EXTERNAL_SOURCE_TYPES = {
    "external_api", "tool_output", "user_input", "third_party",
    "federation", "import", "migration", "sync",
}


def derive_is_self_authored(
    entry: dict,
    request_agent_id: str = "",
) -> Optional[bool]:
    """Derive whether an entry was self-authored from provenance metadata.

    Returns:
        True:  likely self-authored (shallow chain, no external source evidence)
        False: external source evidence (deep chain, external source type, or origin mismatch)
        None:  insufficient metadata to determine

    Heuristic (from R12 mismatch diagnosis):
        - provenance_chain depth ≤ 1 → self-authored signal
        - source type in _EXTERNAL_SOURCE_TYPES → external signal
        - source_declared_origin != source_actual_origin → external signal
        - sync_source_id present and != agent_id → external signal
    """
    chain = entry.get("provenance_chain")
    if isinstance(chain, list):
        chain_depth = len(chain)
    else:
        chain_depth = 0

    # External evidence: deep provenance chain (depth > 1)
    if chain_depth > 1:
        return False

    # External evidence: source type indicates external origin
    source = entry.get("source", "")
    if isinstance(source, str) and source.lower() in _EXTERNAL_SOURCE_TYPES:
        return False
    if isinstance(source, dict):
        # Structured source with declared/actual origin
        declared = source.get("declared_origin", "")
        actual = source.get("actual_origin", "")
        if declared and actual and declared != actual:
            return False  # Origin mismatch = external tampering

    # External evidence: source_declared_origin vs source_actual_origin mismatch
    declared_origin = entry.get("source_declared_origin", "")
    actual_origin = entry.get("source_actual_origin", "")
    if declared_origin and actual_origin and declared_origin != actual_origin:
        return False

    # External evidence: sync_source_id present and different from request agent
    sync_source = entry.get("sync_source_id", "")
    if sync_source and request_agent_id and sync_source != request_agent_id:
        return False

    # Self-authored signal: shallow chain (0 or 1) + no external indicators
    if chain_depth <= 1:
        return True

    # Insufficient metadata
    return None
