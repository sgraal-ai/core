from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .omega_mem import MemoryEntry, PreflightResult, HealingAction

GROKGUARD_VERSION = "v2"

# Grok-specific action priority overrides.
# Grok prefers fresh data — REFETCH always gets highest priority.
_GROK_ACTION_PRIORITY = {
    "REFETCH": 0,
    "VERIFY_WITH_SOURCE": 1,
    "REBUILD_WORKING_SET": 2,
}


@dataclass
class GrokGuardResult:
    preflight: PreflightResult
    grokguard_activated: bool
    grokguard_version: str


class GrokGuard:
    """Grok-specific optimization layer for Sgraal preflight scoring.

    When activated, GrokGuard re-orders the repair plan to prioritize
    REFETCH actions (Grok prefers fresh data over rebuilding working sets)
    and boosts priority of REFETCH on stale tool_state entries.
    """

    def optimize(self, result: PreflightResult, entries: list[MemoryEntry]) -> GrokGuardResult:
        """Apply GrokGuard optimizations to a preflight result."""

        has_stale_tool_state = any(
            e.type == "tool_state" and e.timestamp_age_days > 1
            for e in entries
        )

        if not has_stale_tool_state and not result.repair_plan:
            return GrokGuardResult(
                preflight=result,
                grokguard_activated=False,
                grokguard_version=GROKGUARD_VERSION,
            )

        # Boost REFETCH priority for stale tool_state entries
        optimized_plan: list[HealingAction] = []
        for action in result.repair_plan:
            if action.action == "REFETCH":
                optimized_plan.append(HealingAction(
                    action=action.action,
                    entry_id=action.entry_id,
                    reason=action.reason,
                    projected_improvement=action.projected_improvement,
                    priority=1,  # always highest for Grok
                ))
            else:
                optimized_plan.append(action)

        # Sort by Grok-specific action priority, then standard priority
        optimized_plan.sort(
            key=lambda h: (_GROK_ACTION_PRIORITY.get(h.action, 9), h.priority, -h.projected_improvement)
        )

        optimized_result = PreflightResult(
            omega_mem_final=result.omega_mem_final,
            recommended_action=result.recommended_action,
            assurance_score=result.assurance_score,
            explainability_note=result.explainability_note,
            component_breakdown=result.component_breakdown,
            repair_plan=optimized_plan,
            healing_counter=result.healing_counter,
        )

        return GrokGuardResult(
            preflight=optimized_result,
            grokguard_activated=True,
            grokguard_version=GROKGUARD_VERSION,
        )
