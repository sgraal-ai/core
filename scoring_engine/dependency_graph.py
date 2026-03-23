from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Step:
    step_id: str
    entry_ids: list[str]


@dataclass
class SurgicalResult:
    blocked_steps: list[str]
    safe_steps: list[str]
    partial_execution_possible: bool


class MemoryDependencyGraph:
    """Tracks which workflow steps depend on which memory entries.

    Enables surgical BLOCK — only halt the steps that depend on
    stale/blocked entries, while allowing unaffected steps to proceed.
    """

    def __init__(self) -> None:
        self._steps: dict[str, list[str]] = {}  # step_id → entry_ids
        self._entry_to_steps: dict[str, list[str]] = {}  # entry_id → step_ids

    def add_step(self, step_id: str, entry_ids: list[str]) -> None:
        self._steps[step_id] = entry_ids
        for eid in entry_ids:
            self._entry_to_steps.setdefault(eid, []).append(step_id)

    def get_affected_steps(self, entry_id: str) -> list[str]:
        """Which steps are affected if this entry is stale/blocked."""
        return list(self._entry_to_steps.get(entry_id, []))

    def get_safe_steps(self, blocked_entries: list[str]) -> list[str]:
        """Steps that have no dependency on any blocked entry."""
        blocked_set = set(blocked_entries)
        return [
            sid for sid, eids in self._steps.items()
            if not any(eid in blocked_set for eid in eids)
        ]

    def surgical_block(
        self,
        blocked_entries: list[str],
    ) -> SurgicalResult:
        """Compute which steps must halt and which can proceed."""
        blocked_set = set(blocked_entries)
        blocked_steps: list[str] = []
        safe_steps: list[str] = []

        for sid, eids in self._steps.items():
            if any(eid in blocked_set for eid in eids):
                blocked_steps.append(sid)
            else:
                safe_steps.append(sid)

        return SurgicalResult(
            blocked_steps=blocked_steps,
            safe_steps=safe_steps,
            partial_execution_possible=len(safe_steps) > 0 and len(blocked_steps) > 0,
        )
