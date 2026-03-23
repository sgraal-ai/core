from __future__ import annotations

from contextlib import contextmanager
from typing import Generator


class StepTracker:
    """Tracks memory access per step for automatic dependency detection.

    Usage:
        tracker = StepTracker()
        with tracker.step("step_1"):
            result = client.preflight(memory_state=[...])
            # entries are automatically tracked

        # Send tracked dependencies with next preflight
        steps = tracker.get_steps()
    """

    def __init__(self) -> None:
        self._steps: dict[str, list[str]] = {}
        self._current_step: str | None = None

    @contextmanager
    def step(self, step_id: str) -> Generator[None, None, None]:
        """Context manager that tracks memory access for a step."""
        self._current_step = step_id
        self._steps.setdefault(step_id, [])
        try:
            yield
        finally:
            self._current_step = None

    def track(self, entry_id: str) -> None:
        """Record that the current step accessed entry_id."""
        if self._current_step is not None:
            if entry_id not in self._steps[self._current_step]:
                self._steps[self._current_step].append(entry_id)

    def track_entries(self, entry_ids: list[str]) -> None:
        """Record that the current step accessed multiple entries."""
        for eid in entry_ids:
            self.track(eid)

    def get_steps(self) -> list[dict[str, object]]:
        """Return steps in the format expected by POST /v1/preflight."""
        return [
            {"step_id": sid, "entry_ids": eids}
            for sid, eids in self._steps.items()
        ]

    def reset(self) -> None:
        """Clear all tracking state."""
        self._steps.clear()
        self._current_step = None
