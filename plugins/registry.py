"""Plugin registry — tracks installed and activated plugins.

ACTIVATION IS PER-TENANT. The registry maintains a single global catalog of
INSTALLED plugins (plugin code, deployed via CI/CD) but a **per-tenant** set of
ACTIVE plugins. Tenant A enabling a plugin cannot affect tenant B's preflight
calls — that would be a cross-tenant data/behavior leak.

A special tenant key `_GLOBAL` is reserved for server-wide defaults that the
operator turns on at startup (e.g., via `SGRAAL_PLUGIN_DIR` + `activate=True`
in the loader). All other tenants start with no active plugins and must
explicitly activate via `POST /v1/plugins/activate`.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from .base import SgraalPlugin, PluginResult, HOOK_NAMES

logger = logging.getLogger("sgraal.plugins")


# Tenant key used for operator-defined defaults at startup (examples loader,
# SGRAAL_PLUGIN_DIR). Production tenants identify themselves via their
# _safe_key_hash. Use of this constant by non-startup code is a red flag.
GLOBAL_TENANT = "_GLOBAL"


class PluginRegistry:
    """Thread-safe in-memory registry with global install + per-tenant activation.

    - INSTALLED plugins (code) are global: `_installed: dict[name, SgraalPlugin]`
    - ACTIVE plugins are per-tenant: `_active_by_tenant: dict[tenant, set[name]]`

    Call sites must pass a tenant key to every activation/query. The empty
    default (`tenant=None`) is interpreted as "nobody" (empty active set) for
    hook execution and as `GLOBAL_TENANT` for startup loading.
    """

    HOOK_BUDGET_MS: float = 10.0

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._installed: dict[str, SgraalPlugin] = {}
        # tenant_id -> {plugin_name}. Lookups default to empty set.
        self._active_by_tenant: dict[str, set[str]] = {}

    # --- Installation ---------------------------------------------------

    def register(
        self,
        plugin: SgraalPlugin,
        activate: bool = True,
        tenant: Optional[str] = None,
    ) -> None:
        """Install a plugin. If activate=True, also mark it active for `tenant`.

        `tenant=None` with `activate=True` activates the plugin for GLOBAL_TENANT
        only — used by startup code to flip operator-supplied defaults on.
        """
        if not isinstance(plugin, SgraalPlugin):
            raise TypeError(f"Plugin must inherit from SgraalPlugin, got {type(plugin).__name__}")
        if not plugin.name or plugin.name == "unnamed_plugin":
            raise ValueError(f"Plugin {type(plugin).__name__} must set a `name` class attribute")
        scope = tenant if tenant is not None else GLOBAL_TENANT
        with self._lock:
            self._installed[plugin.name] = plugin
            if activate:
                self._active_by_tenant.setdefault(scope, set()).add(plugin.name)
        logger.info(
            "Plugin installed: %s v%s (active_for=%s, hooks=%s)",
            plugin.name, plugin.version, scope if activate else "none", plugin.hooks,
        )

    def unregister(self, name: str) -> bool:
        """Remove a plugin from the registry. Removes it from EVERY tenant's
        active set. Returns True if it existed."""
        with self._lock:
            existed = name in self._installed
            self._installed.pop(name, None)
            for active_set in self._active_by_tenant.values():
                active_set.discard(name)
        if existed:
            logger.info("Plugin uninstalled: %s (from all tenants)", name)
        return existed

    # --- Activation -----------------------------------------------------

    def activate(self, name: str, tenant: Optional[str] = None) -> bool:
        """Mark an installed plugin as active for `tenant`.
        Returns True on success, False if the plugin isn't installed."""
        scope = tenant if tenant is not None else GLOBAL_TENANT
        with self._lock:
            if name not in self._installed:
                return False
            self._active_by_tenant.setdefault(scope, set()).add(name)
        logger.info("Plugin activated: %s for tenant=%s", name, scope)
        return True

    def deactivate(self, name: str, tenant: Optional[str] = None) -> bool:
        """Mark a plugin as inactive for `tenant`. The plugin remains installed
        and may still be active for OTHER tenants. Returns True if it was
        active for this tenant."""
        scope = tenant if tenant is not None else GLOBAL_TENANT
        with self._lock:
            active_set = self._active_by_tenant.get(scope)
            if not active_set or name not in active_set:
                return False
            active_set.discard(name)
            if not active_set:
                self._active_by_tenant.pop(scope, None)
        logger.info("Plugin deactivated: %s for tenant=%s", name, scope)
        return True

    # --- Queries --------------------------------------------------------

    def list_plugins(self, tenant: Optional[str] = None) -> list[dict[str, Any]]:
        """Return metadata for all installed plugins with their active state
        for the given tenant. If tenant=None, reports GLOBAL_TENANT state."""
        scope = tenant if tenant is not None else GLOBAL_TENANT
        with self._lock:
            active_for_scope = self._active_by_tenant.get(scope, set())
            return [
                {**plugin.describe(), "active": name in active_for_scope, "tenant_scope": scope}
                for name, plugin in self._installed.items()
            ]

    def get_plugin(self, name: str) -> Optional[SgraalPlugin]:
        with self._lock:
            return self._installed.get(name)

    def active_plugins(self, tenant: Optional[str] = None) -> list[SgraalPlugin]:
        """Snapshot list of plugin instances active for `tenant`.
        `tenant=None` → empty list (no implicit global activation for production)."""
        if tenant is None:
            return []
        with self._lock:
            active_names = self._active_by_tenant.get(tenant, set())
            return [self._installed[n] for n in active_names if n in self._installed]

    def is_active(self, name: str, tenant: Optional[str] = None) -> bool:
        scope = tenant if tenant is not None else GLOBAL_TENANT
        with self._lock:
            return name in self._active_by_tenant.get(scope, set())

    def reset(self) -> None:
        """Clear the registry. For tests only."""
        with self._lock:
            self._installed.clear()
            self._active_by_tenant.clear()

    # --- Hook execution -------------------------------------------------

    def run_hook(
        self,
        hook_name: str,
        *args: Any,
        collect_results: Optional[list[PluginResult]] = None,
        default: Any = None,
        tenant: Optional[str] = None,
    ) -> Any:
        """Run a hook across plugins active for `tenant`.

        `tenant=None` → hook runs NO plugins (fail-closed default for safety).
        Pass the caller's tenant key (e.g. `_safe_key_hash(key_record)`) to
        enable tenant-scoped plugin execution.
        """
        if hook_name not in HOOK_NAMES:
            raise ValueError(f"Unknown hook: {hook_name}")

        plugins = self.active_plugins(tenant=tenant)
        if not plugins:
            return default if hook_name == "on_preflight_start" else args[-1] if hook_name == "on_component_score" else (args[0], args[1]) if hook_name == "on_omega_computed" else args[0] if hook_name == "on_preflight_complete" else default

        current_value: Any = None
        if hook_name == "on_component_score":
            current_value = args[1]
        elif hook_name == "on_omega_computed":
            current_value = (args[0], args[1])
        elif hook_name == "on_preflight_complete":
            current_value = args[0]

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
