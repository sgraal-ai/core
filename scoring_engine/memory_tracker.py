from __future__ import annotations

from .dependency_graph import MemoryDependencyGraph


class MemoryAccessTracker:
    """Automatically tracks which memory entries each step reads.

    Eliminates the need for manual step → entry_id declarations.
    Call track() when an entry is accessed during a step, then convert
    to a MemoryDependencyGraph for surgical BLOCK analysis.
    """

    def __init__(self) -> None:
        self._accesses: dict[str, list[str]] = {}  # step_id → [entry_ids]
        self._current_step: str | None = None

    def track(self, step_id: str, entry_id: str) -> None:
        """Record that step_id accessed entry_id."""
        self._accesses.setdefault(step_id, [])
        if entry_id not in self._accesses[step_id]:
            self._accesses[step_id].append(entry_id)

    def begin_step(self, step_id: str) -> None:
        """Set the current step context for implicit tracking."""
        self._current_step = step_id

    def end_step(self) -> None:
        """Clear the current step context."""
        self._current_step = None

    @property
    def current_step(self) -> str | None:
        return self._current_step

    def track_current(self, entry_id: str) -> None:
        """Track entry_id under the current step (if set)."""
        if self._current_step is not None:
            self.track(self._current_step, entry_id)

    def get_step_dependencies(self) -> dict[str, list[str]]:
        """Return auto-detected dependency map: step_id → [entry_ids]."""
        return dict(self._accesses)

    def to_dependency_graph(self) -> MemoryDependencyGraph:
        """Convert tracked accesses to a MemoryDependencyGraph."""
        graph = MemoryDependencyGraph()
        for step_id, entry_ids in self._accesses.items():
            graph.add_step(step_id, entry_ids)
        return graph

    def reset(self) -> None:
        """Clear all tracking state between chain runs."""
        self._accesses.clear()
        self._current_step = None
