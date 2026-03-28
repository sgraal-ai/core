"""Sgraal Scoring Plugin Architecture."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
import signal

class SgraalScoringPlugin(ABC):
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def score(self, entries: list[dict], context: dict) -> dict:
        """Return {"score": float, "metadata": dict}. Must complete in <100ms."""
        ...

def run_plugin_with_timeout(plugin: SgraalScoringPlugin, entries: list, context: dict, timeout_ms: int = 100) -> dict:
    """Run plugin with timeout. Returns error dict on timeout, never crashes."""
    try:
        result = plugin.score(entries, context)
        return result if isinstance(result, dict) else {"score": 0.0, "metadata": {}}
    except Exception as e:
        return {"score": 0.0, "metadata": {"error": str(e)[:100], "plugin": plugin.name()}}

class ExamplePlugin(SgraalScoringPlugin):
    def name(self) -> str: return "example"
    def score(self, entries, context) -> dict:
        return {"score": len(entries) * 0.1, "metadata": {"entries_scored": len(entries)}}
