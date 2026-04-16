"""Plugin loading from filesystem or installed packages.

This module loads plugin CODE from trusted sources (filesystem directories
or installed Python packages). It does NOT accept arbitrary code over HTTP —
see SECURITY_MODEL in base.py for the rationale.
"""
from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
import os
from pathlib import Path
from typing import Optional

from .base import SgraalPlugin
from .registry import registry

logger = logging.getLogger("sgraal.plugins.loader")


def load_from_directory(path: str, activate: bool = False) -> list[str]:
    """Load every *.py file in `path` and register any SgraalPlugin subclasses.

    Returns the list of registered plugin names.

    Security: `path` MUST be a trusted directory (baked into the image or
    mounted by an operator). Callers are responsible for validating the path.
    """
    dir_path = Path(path).resolve()
    if not dir_path.exists() or not dir_path.is_dir():
        logger.warning("Plugin directory does not exist: %s", dir_path)
        return []

    registered: list[str] = []
    for py_file in sorted(dir_path.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        module_name = f"sgraal_plugin_{py_file.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            logger.error("Failed to load plugin file %s: %s", py_file, e)
            continue

        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if obj is SgraalPlugin:
                continue
            if not issubclass(obj, SgraalPlugin):
                continue
            try:
                instance = obj()
            except Exception as e:
                logger.error("Failed to instantiate plugin %s: %s", obj.__name__, e)
                continue
            try:
                registry.register(instance, activate=activate)
                registered.append(instance.name)
            except Exception as e:
                logger.error("Failed to register plugin %s: %s", obj.__name__, e)

    return registered


def load_from_package(package_name: str, activate: bool = False) -> list[str]:
    """Import a package and register any SgraalPlugin subclasses found at
    its top level.

    Example: `load_from_package("sgraal_plugin_acme")` imports `sgraal_plugin_acme`
    and registers any SgraalPlugin subclasses defined there.

    Security: the package MUST be pre-installed (via pip install). This
    function does NOT install packages. Callers should pre-validate via an
    allowlist if untrusted input can reach this function.
    """
    try:
        module = importlib.import_module(package_name)
    except ImportError as e:
        logger.error("Cannot import plugin package %s: %s", package_name, e)
        return []

    registered: list[str] = []
    for _name, obj in inspect.getmembers(module, inspect.isclass):
        if obj is SgraalPlugin:
            continue
        if not issubclass(obj, SgraalPlugin):
            continue
        try:
            instance = obj()
            registry.register(instance, activate=activate)
            registered.append(instance.name)
        except Exception as e:
            logger.error("Failed to register plugin %s from %s: %s",
                         obj.__name__, package_name, e)
    return registered


def load_examples(activate: bool = False) -> list[str]:
    """Load the bundled example plugins. Installed but not activated by default."""
    examples_dir = Path(__file__).parent / "examples"
    return load_from_directory(str(examples_dir), activate=activate)
