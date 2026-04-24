"""Explicit 4-invariant validation layer — fast-path BLOCK on clear violations.

Sgraal enforces 4 memory integrity invariants:
  I1 Identity Invariance — entries must not claim contradictory identities
  I2 Time Validity — timestamps must be physically plausible
  I3 Evidence Independence — entries from the same source must not dominate
  I4 Provenance Integrity — provenance chains must be structurally valid

This module checks all 4 invariants before the full 83-module pipeline runs.
If any invariant shows a "clear_violation" (conservative threshold), the
preflight can fast-path to BLOCK without running the full pipeline.

Clear violations are intentionally rare — they represent structural
impossibilities (not statistical anomalies) that no legitimate memory
state could exhibit.
"""
from __future__ import annotations

import re
from typing import Optional


_PAST_YEAR = re.compile(r'\b(20[0-9][0-9])\b')


def check_invariants(
    memory_state: list,
    action_type: str = "reversible",
    current_year: int = 2026,
) -> dict:
    """Check 4 structural invariants on the memory state.

    Returns dict with keys:
        i1_identity, i2_time, i3_evidence, i4_provenance
    Each value is "ok", "clear_violation", or "ambiguous".
    Also includes "fast_path_block" (bool) and "violated_invariant" (str or None).
    """
    entries = []
    for e in memory_state:
        if isinstance(e, dict):
            entries.append(e)
        else:
            entries.append({
                "id": getattr(e, "id", ""),
                "content": getattr(e, "content", ""),
                "type": getattr(e, "type", "semantic"),
                "timestamp_age_days": getattr(e, "timestamp_age_days", 0),
                "source_trust": getattr(e, "source_trust", 0.5),
                "source_conflict": getattr(e, "source_conflict", 0),
                "downstream_count": getattr(e, "downstream_count", 0),
                "provenance_chain": getattr(e, "provenance_chain", []),
            })

    n = len(entries)
    result = {
        "i1_identity": "ok",
        "i2_time": "ok",
        "i3_evidence": "ok",
        "i4_provenance": "ok",
        "fast_path_block": False,
        "violated_invariant": None,
        "entries_checked": n,
    }

    if n == 0:
        return result

    # I1: Identity Invariance — same entry ID must not appear with different content
    ids_seen: dict[str, str] = {}
    for e in entries:
        eid = e.get("id", "")
        content = e.get("content", "")
        if eid and eid in ids_seen and ids_seen[eid] != content:
            result["i1_identity"] = "clear_violation"
            result["fast_path_block"] = True
            result["violated_invariant"] = "I1"
            return result
        if eid:
            ids_seen[eid] = content

    # I2: Time Validity — negative age is physically impossible;
    # age=0 with many historical year references is suspicious but not clear violation
    for e in entries:
        age = e.get("timestamp_age_days", 0)
        if isinstance(age, (int, float)) and age < -1:
            result["i2_time"] = "clear_violation"
            result["fast_path_block"] = True
            result["violated_invariant"] = "I2"
            return result

    # I2 ambiguous: age=0 with 3+ past-year markers in a single entry
    for e in entries:
        age = e.get("timestamp_age_days", 0)
        content = e.get("content", "")
        if age == 0 and isinstance(content, str):
            years = _PAST_YEAR.findall(content)
            past_years = [int(y) for y in years if int(y) < current_year]
            if len(past_years) >= 3:
                result["i2_time"] = "ambiguous"

    # I3: Evidence Independence — if >80% of entries share the exact same source_trust
    # AND the exact same source_conflict, they are not independent evidence
    if n >= 4:
        trust_conflict_pairs = [(e.get("source_trust", 0.5), e.get("source_conflict", 0)) for e in entries]
        from collections import Counter
        pair_counts = Counter(trust_conflict_pairs)
        most_common_count = pair_counts.most_common(1)[0][1]
        if most_common_count / n > 0.8:
            result["i3_evidence"] = "ambiguous"  # Suspicious but not clear violation

    # I4: Provenance Integrity — circular reference is a clear violation
    for e in entries:
        chain = e.get("provenance_chain", [])
        if isinstance(chain, list) and len(chain) != len(set(chain)):
            result["i4_provenance"] = "clear_violation"
            result["fast_path_block"] = True
            result["violated_invariant"] = "I4"
            return result

    return result
