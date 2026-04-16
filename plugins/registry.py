"""Plugin registry — tracks installed and activated plugins."""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from .base import SgraalPlugin, PluginResult, HOOK_NAMES

logger = logging.getLogger("sgraal.plugins")


class PluginRegistry:
    """Thread-safe in-memory registry of Sgraal plugins.

    Plugins have two states: INSTALLED (class/instance is known to the registry)
    and ACTIVE (actively participating in preflight hooks). Activation is a
    runtime control; installation is a code-deployment concern.

    The registry is a singleton (module-level `registry` instance).
    """

    # Per-hook budget (advisory; see SECURITY_MODEL in base.py)
    HOOK_BUDGET_MS: float = 10.0

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._installed: dict[str, SgraalPlugin] = {}
        self._active: set[str] = set()

    # --- Installation ---------------------------------------------------

    def register(self, plugin: SgraalPlugin, activate: bool = True) -> None:
        """Install a plugin instance. If activate=True, also mark it active."""
        if not isinstance(plugin, SgraalPlugin):
            raise TypeError(f"Plugin must inherit from SgraalPlugin, got {type(plugin).__name__}")
        if not plugin.name or plugin.name == "unnamed_plugin":
            raise ValueError(f"Plugin {type(plugin).__name__} must set a `name` class attribute")
        with self._lock:
            self._installed[plugin.name] = plugin
            if activate:
                self._active.add(plugin.name)
        logger.info("Plugin installed: %s v%s (active=%s, hooks=%s)",
                    plugin.name, plugin.version, activate, plugin.hooks)

    def unregister(self, name: str) -> bool:
        """Remove a plugin from the registry. Returns True if it existed."""
        with self._lock:
            existed = name in self._installed
            self._installed.pop(name, None)
            self._active.discard(name)
        if existed:
            logger.info("Plugin uninstalled: %s", name)
        return existed

    # --- Activation -----------------------------------------------------

    def activate(self, name: str) -> bool:
        """Mark an installed plugin as active. Returns True if it became active.
        Returns False if the plugin isn't installed."""
        with self._lock:
            if name not in self._installed:
                return False
            self._active.add(name)
        logger.info("Plugin activated: %s", name)
        return True

    def deactivate(self, name: str) -> bool:
        """Mark a plugin as inactive. Returns True if it was active."""
        with self._lock:
            was_active = name in self._active
            self._active.discard(name)
        if was_active:
            logger.info("Plugin deactivated: %s", name)
        return was_active

    # --- Queries --------------------------------------------------------

    def list_plugins(self) -> list[dict[str, Any]]:
        """Return metadata for all installed plugins, with active status."""
        with self._lock:
            return [
                {**plugin.describe(), "active": name in self._active}
                for name, plugin in self._installed.items()
            ]

    def get_plugin(self, name: str) -> Optional[SgraalPlugin]:
        with self._lock:
            return self._installed.get(name)

    def active_plugins(self) -> list[SgraalPlugin]:
        """Snapshot list of active plugin instances (thread-safe)."""
        with self._lock:
            return [self._installed[n] for n in self._active if n in self._installed]

    def is_active(self, name: str) -> bool:
        with self._lock:
            return name in self._active

    def reset(self) -> None:
        """Clear the registry. For tests only."""
        with self._lock:
            self._installed.clear()
            self._active.clear()

    # --- Hook execution -------------------------------------------------

    def run_hook(
        self,
        hook_name: str,
        *args: Any,
        collect_results: Optional[list[PluginResult]] = None,
        default: Any = None,
    ) -> Any:
        """Run a hook across all active plugins.

        Each plugin's hook is wrapped in try/except. Duration is measured
        post-hoc; exceeding HOOK_BUDGET_MS is logged as a warning but does
        not interrupt the hook (Python cannot interrupt CPU-bound code in
        the same process).

        For hooks that return a transformed value (on_component_score,
        on_omega_computed, on_preflight_complete), the value is threaded
        through plugins sequentially: plugin_k's output becomes plugin_{k+1}'s
        input.

        For on_preflight_start (no return value), plugins are called in order
        but results are discarded.

        Returns the final transformed value. Populates `collect_results` if
        provided.
        """
        if hook_name not in HOOK_NAMES:
            raise ValueError(f"Unknown hook: {hook_name}")

        plugins = self.active_plugins()
        if not plugins:
            return default if hook_name == "on_preflight_start" else args[-1] if hook_name == "on_component_score" else (args[0], args[1]) if hook_name == "on_omega_computed" else args[0] if hook_name == "on_preflight_complete" else default

        current_value: Any = None
        if hook_name == "on_component_score":
            # args = (component_name, score, memory_state); we transform score
            current_value = args[1]
        elif hook_name == "on_omega_computed":
            # args = (omega, decision, context); we transform (omega, decision)
            current_value = (args[0], args[1])
        elif hook_name == "on_preflight_complete":
            # args = (result,); we transform result
            current_value = args[0]
        # on_preflight_start has no current_value

        for plugin in plugins:
            if hook_name not in plugin.hooks:
                continue
            method = getattr(plugin, hook_name)
            t0 = time.perf_counter()
            result = PluginResult(plugin=plugin.name, hook=hook_name)
            try:
                if hook_name == "on_preflight_start":
                    method(*args)
                elif hook_name == "on_component_score":
                    # (component_name, score, memory_state) — pass updated score
                    before = current_value
                    after = method(args[0], current_value, args[2])
                    if not isinstance(after, (int, float)):
                        raise TypeError(f"on_component_score must return a number, got {type(after).__name__}")
                    after = max(0.0, min(100.0, float(after)))
                    if abs(after - before) > 1e-9:
                        result.modified = True
                        result.delta = after - before
                    current_value = after
                elif hook_name == "on_omega_computed":
                    before_omega, before_decision = current_value
                    after = method(current_value[0], current_value[1], args[2])
                    if not (isinstance(after, tuple) and len(after) == 2):
                        raise TypeError(f"on_omega_computed must return (omega, decision) tuple")
                    new_omega = max(0.0, min(100.0, float(after[0])))
                    new_decision = str(after[1])
                    if abs(new_omega - before_omega) > 1e-9 or new_decision != before_decision:
                        result.modified = True
                        result.delta = new_omega - before_omega
                        result.extra = {"decision_before": before_decision, "decision_after": new_decision}
                    current_value = (new_omega, new_decision)
                elif hook_name == "on_preflight_complete":
                    before_keys = set(current_value.keys()) if isinstance(current_value, dict) else set()
                    after = method(current_value)
                    if not isinstance(after, dict):
                        raise TypeError(f"on_preflight_complete must return a dict, got {type(after).__name__}")
                    new_keys = set(after.keys()) - before_keys
                    if new_keys:
                        result.modified = True
                        result.extra = {"new_keys": sorted(new_keys)[:10]}
                    current_value = after
            except Exception as e:
                result.error = f"{type(e).__name__}: {str(e)[:150]}"
                logger.warning("Plugin %s.%s raised: %s", plugin.name, hook_name, result.error)
                # Pass-through on error — don't let plugin failure break preflight
            finally:
                result.duration_ms = (time.perf_counter() - t0) * 1000.0
                if result.duration_ms > self.HOOK_BUDGET_MS:
                    logger.warning(
                        "Plugin %s.%s exceeded %sms budget: %.2fms",
                        plugin.name, hook_name, self.HOOK_BUDGET_MS, result.duration_ms,
                    )
                    if not result.error:
                        result.error = f"budget_exceeded_{self.HOOK_BUDGET_MS}ms"
                if collect_results is not None:
                    collect_results.append(result)

        return current_value


# Module-level singleton
registry = PluginRegistry()
