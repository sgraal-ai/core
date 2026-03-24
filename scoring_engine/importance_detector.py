from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Optional

from .omega_mem import MemoryEntry, compute as _compute


@dataclass
class ImportanceResult:
    entry_id: str
    importance_score: float  # 0.0–10.0
    at_risk: bool
    warning: Optional[str]
    signal_breakdown: dict
    voi_score: float = 0.0  # Value of Information: expected Ω_MEM improvement if healed


# Freshness thresholds per memory type (days).
# An entry is "at risk" when age exceeds 70% of the threshold.
FRESHNESS_THRESHOLDS = {
    "tool_state":       7,
    "shared_workflow":  14,
    "episodic":         30,
    "preference":       60,
    "semantic":         100,
    "policy":           200,
    "identity":         500,
}
FRESHNESS_THRESHOLD_DEFAULT = 30

# Signal weights (sum to 10.0 for easy 0–10 scoring)
W_RETURN_FREQUENCY = 2.5
W_BLAST_RADIUS     = 3.0
W_IRREVERSIBILITY  = 2.5
W_UNIQUENESS       = 2.0

# Irreversibility multipliers
IRREVERSIBILITY_SCORES = {
    "irreversible": 1.0,
    "reversible":   0.4,
    "advisory":     0.1,
}


def compute_importance(entry: MemoryEntry) -> ImportanceResult:
    """Compute 4-signal importance score for a single memory entry.

    Signals:
        1. return_frequency — how often the entry is referenced
        2. blast_radius — downstream_count impact
        3. irreversibility — action context severity
        4. uniqueness — user_stated with no backup = highest weight
    """

    # Signal 1: return_frequency (0–1, capped at 10 references)
    freq_signal = min(1.0, entry.reference_count / 10.0)

    # Signal 2: blast_radius (0–1, capped at 10 downstream)
    blast_signal = min(1.0, entry.downstream_count / 10.0)

    # Signal 3: irreversibility (0–1)
    irrev_signal = IRREVERSIBILITY_SCORES.get(entry.action_context, 0.4)

    # Signal 4: uniqueness — user_stated + no backup = 1.0
    if entry.source == "user_stated" and not entry.has_backup_source:
        unique_signal = 1.0
    elif entry.source == "user_stated":
        unique_signal = 0.5
    elif not entry.has_backup_source:
        unique_signal = 0.6
    else:
        unique_signal = 0.1

    # Weighted importance score (0–10)
    importance = (
        freq_signal   * W_RETURN_FREQUENCY
        + blast_signal  * W_BLAST_RADIUS
        + irrev_signal  * W_IRREVERSIBILITY
        + unique_signal * W_UNIQUENESS
    )
    importance = round(min(10.0, max(0.0, importance)), 1)

    signals = {
        "return_frequency": round(freq_signal, 3),
        "blast_radius": round(blast_signal, 3),
        "irreversibility": round(irrev_signal, 3),
        "uniqueness": round(unique_signal, 3),
    }

    # At-risk detection
    threshold = FRESHNESS_THRESHOLDS.get(entry.type, FRESHNESS_THRESHOLD_DEFAULT)
    age_ratio = entry.timestamp_age_days / threshold if threshold > 0 else 0
    at_risk = importance >= 5.0 and age_ratio >= 0.7

    # Top signal reason — derived from whichever signal scored highest
    signal_reasons = {
        "return_frequency": "frequently referenced",
        "blast_radius": "many downstream decisions depend on it",
        "irreversibility": "used in irreversible actions",
        "uniqueness": "only known from a single source",
    }
    top_signal = max(signals, key=signals.get)
    top_reason = signal_reasons[top_signal]

    warning = None
    if at_risk:
        content_preview = entry.content[:60] + ("..." if len(entry.content) > 60 else "")
        warning = (
            f"\u26a0\ufe0f Memory at risk: '{content_preview}' "
            f"({entry.timestamp_age_days:.0f} days old, {top_reason}). "
            f"Consider refreshing before proceeding."
        )

    return ImportanceResult(
        entry_id=entry.id,
        importance_score=importance,
        at_risk=at_risk,
        warning=warning,
        signal_breakdown=signals,
        voi_score=0.0,  # computed by compute_importance_with_voi when full context available
    )


def compute_importance_with_voi(
    entries: list[MemoryEntry],
    action_type: str = "reversible",
    domain: str = "general",
) -> list[ImportanceResult]:
    """Compute importance + Value of Information for all entries.

    VoI = E[U(act|healed)] - E[U(act)] = omega_current - omega_with_entry_healed

    Higher VoI means healing this entry gives the biggest Ω_MEM improvement.
    Results sorted by VoI descending (highest ROI first).
    """
    if not entries:
        return []

    # Current Ω_MEM with all entries as-is
    current = _compute(entries, action_type, domain)
    omega_current = current.omega_mem_final

    results: list[ImportanceResult] = []
    for i, entry in enumerate(entries):
        base = compute_importance(entry)

        # Compute VoI: score with this entry "healed" (fresh, trusted, no conflict)
        healed_entry = copy.copy(entry)
        healed_entry.timestamp_age_days = 0
        healed_entry.source_trust = 1.0
        healed_entry.source_conflict = 0.0
        healed_entry.r_belief = 1.0

        healed_entries = list(entries)
        healed_entries[i] = healed_entry
        healed_result = _compute(healed_entries, action_type, domain)
        omega_healed = healed_result.omega_mem_final

        voi = round(max(0, omega_current - omega_healed), 2)

        results.append(ImportanceResult(
            entry_id=base.entry_id,
            importance_score=base.importance_score,
            at_risk=base.at_risk,
            warning=base.warning,
            signal_breakdown=base.signal_breakdown,
            voi_score=voi,
        ))

    # Sort by VoI descending (highest ROI first)
    results.sort(key=lambda r: -r.voi_score)
    return results
