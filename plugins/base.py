"""Sgraal plugin base class and common types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# SECURITY_MODEL
# ---------------------------------------------------------------------------
# Plugins are FULLY TRUSTED CODE. They run in the same process as the Sgraal
# API server with the same privileges. A malicious or buggy plugin can:
#   - Read env vars (including secrets)
#   - Make arbitrary filesystem and network calls
#   - Crash the worker process
#   - Modify preflight decisions in non-deterministic ways
#
# The plugin system is registry-only: plugin CODE must be installed via CI/CD
# (baked into the container image or pip-installed). The HTTP API only exposes
# activation/deactivation of pre-installed plugins, never code upload.
#
# The preflight pipeline wraps each hook call in try/except with a per-hook
# time-budget check. Plugin failures never crash preflight — the plugin is
# logged and skipped. The time budget is advisory (post-hoc measurement); it
# cannot interrupt a CPU-bound hook mid-execution.
# ---------------------------------------------------------------------------


HOOK_NAMES = (
    "on_preflight_start",
    "on_component_score",
    "on_omega_computed",
    "on_preflight_complete",
)


@dataclass
class PluginResult:
    """One entry in the `plugin_results` list returned by preflight."""
    plugin: str
    hook: str
    modified: bool = False
    delta: float = 0.0
    error: Optional[str] = None
    duration_ms: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "plugin": self.plugin,
            "hook": self.hook,
            "modified": self.modified,
            "delta": round(self.delta, 4),
            "duration_ms": round(self.duration_ms, 3),
        }
        if self.error:
            d["error"] = self.error
        if self.extra:
            d["extra"] = self.extra
        return d


class SgraalPlugin:
    """Base class for Sgraal scoring plugins.

    Subclasses MUST set `name` and `version` as class attributes. Override any
    of the four hook methods below to extend scoring behavior. All hooks are
    optional — the default implementations are no-ops and are recognized as
    "not implemented" by the plugin runner (via identity comparison with the
    base class method).

    Hook semantics:
        on_preflight_start(memory_state, context) -> None
            Called once at the start of every preflight call. Use for setup,
            logging, or side-effect tracking. Return value is ignored.

        on_component_score(component_name, score, memory_state) -> float
            Called after each of the 10 scoring components is computed. The
            return value REPLACES the component score. Return the unchanged
            input to pass through. Score is in [0, 100].

        on_omega_computed(omega, decision, context) -> (omega, decision)
            Called after omega_mem_final and recommended_action are computed.
            The returned tuple REPLACES both. Use cautiously — modifying the
            decision can override the BLOCK boundary and is auditable via
            plugin_results.

        on_preflight_complete(result) -> dict
            Called after the full response is assembled. The returned dict
            REPLACES the response. Use for post-processing, field injection,
            or logging.
    """

    # Subclasses MUST override these two:
    name: str = "unnamed_plugin"
    version: str = "0.0.0"

    @property
    def hooks(self) -> list[str]:
        """Return the list of hooks this plugin implements (non-default methods).

        Determined at property access time by comparing the instance's hook
        methods against the base class's default implementations.
        """
        implemented: list[str] = []
        for hook_name in HOOK_NAMES:
            inst_method = getattr(type(self), hook_name, None)
            base_method = getattr(SgraalPlugin, hook_name, None)
            if inst_method is not None and inst_method is not base_method:
                implemented.append(hook_name)
        return implemented

    def on_preflight_start(self, memory_state: list, context: dict) -> None:
        """Called before scoring begins. Default: no-op."""
        return None

    def on_component_score(self, component_name: str, score: float, memory_state: list) -> float:
        """Called after each component score. Default: pass-through."""
        return score

    def on_omega_computed(self, omega: float, decision: str, context: dict) -> tuple[float, str]:
        """Called after omega + decision. Default: pass-through."""
        return omega, decision

    def on_preflight_complete(self, result: dict) -> dict:
        """Called after response assembly. Default: pass-through."""
        return result

    def describe(self) -> dict[str, Any]:
        """Return plugin metadata for listing endpoints."""
        return {
            "name": self.name,
            "version": self.version,
            "hooks": self.hooks,
            "class": type(self).__name__,
            "module": type(self).__module__,
        }
