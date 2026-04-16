"""Sgraal plugin system — registry-only.

This package provides the plugin architecture for extending Sgraal's scoring
engine with custom logic. The design is intentionally registry-only: plugin
CODE must be installed via normal CI/CD (baked into the container image or
pip-installed), and only plugin ACTIVATION is exposed over HTTP.

Security rationale: Python cannot sandbox in-process code execution. Accepting
arbitrary plugin source via HTTP would be RCE-as-a-service. See
SECURITY_MODEL in `plugins/base.py` for the full security model.

Usage:
    from plugins import SgraalPlugin, registry, loader

    # Register a plugin (programmatic, e.g. in api/main.py startup)
    registry.register(MyPlugin())

    # Load all plugins from a directory (at startup)
    loader.load_from_directory("plugins/examples")

    # From API: POST /v1/plugins/activate {"name": "custom_freshness"}
"""
from .base import SgraalPlugin, PluginResult, HOOK_NAMES
from .registry import registry
from . import loader

__all__ = ["SgraalPlugin", "PluginResult", "HOOK_NAMES", "registry", "loader"]
