#!/usr/bin/env python3
"""CI check: detect endpoints that access tenant-scoped collections without TenantContext.

Usage:
    python3 scripts/check_tenant_isolation.py [--strict]

Modes:
    Default (warn-only): prints warnings but exits 0
    --strict: exits 1 on any violation (enable after 2026-05-01)

    # TODO(2026-05-01): Switch default to --strict mode.
    # After this date, remove warn-only mode and make --strict the default.
    # This gives 7 days from initial deployment (2026-04-23) for migration.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

# Collections that require tenant scoping (from Phase 1.1 inventory)
TENANT_COLLECTIONS = {
    "_outcomes", "_court_verdicts", "_async_jobs", "_twin_jobs",
    "_sleeper_scans", "_truth_subs", "_webhooks", "_memory_uris",
    "_blackbox", "_lifecycle_policies", "_forensics", "_passports",
    "_alert_rules", "_sla_rules", "_templates",
    "_retention_policies", "_async_preflight_jobs",
    "_redteam_jobs", "_lab_jobs", "_snapshots",
    "_snapshot_index", "_clone_history_by_tenant",
    "_atc_agents", "_atc_holds", "_firewall_rules",
    "_firewall_violations", "_consensus_subs",
    "_commons", "_commons_policies", "_commons_activity",
    "_truth_fetch_log",
}

# Endpoints that are exempt from tenant scoping (public, system-wide, or internal)
EXEMPT_FUNCTIONS = {
    # Public/unauthenticated endpoints
    "health", "healthcheck", "root", "well_known_agent",
    "verify_attestation", "verify_provenance", "verify_fidelity",
    "playground_share", "playground_load",
    "get_badge_status",  # Public badge check
    # Internal/system-wide
    "_lifespan", "_run_periodic_cleanup", "_scheduler_scoring_drift",
    "_scheduler_daily_snapshot", "_scheduler_sleeper_scan",
    "_scheduler_stripe_retry", "_scheduler_truth_subscription",
    "_load_benchmark_corpus",
    # Preflight internals (use _pf_tenant directly)
    "_preflight_internal", "_finalize_decision", "_set_action",
}

# Dependency names that indicate tenant scoping
TENANT_DEPS = {"get_tenant_context", "TenantContext"}


def _get_endpoint_decorators(node: ast.FunctionDef) -> list[str]:
    """Extract route decorators like @app.get, @app.post, @router.post, etc."""
    routes = []
    for dec in node.decorator_list:
        if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
            attr = dec.func.attr
            if attr in ("get", "post", "put", "patch", "delete"):
                routes.append(attr)
    return routes


def _references_collection(node: ast.FunctionDef, collections: set[str]) -> set[str]:
    """Find which tenant-scoped collections a function body references."""
    found = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id in collections:
            found.add(child.id)
        elif isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name):
            # Handle module.collection access
            if child.attr in collections:
                found.add(child.attr)
    return found


def _has_tenant_dep(node: ast.FunctionDef) -> bool:
    """Check if the function declares a TenantContext dependency."""
    for arg in node.args.args + node.args.kwonlyargs:
        ann = arg.annotation
        if ann is None:
            continue
        # Check for: tenant: TenantContext = Depends(get_tenant_context)
        if isinstance(ann, ast.Name) and ann.id in TENANT_DEPS:
            return True
        if isinstance(ann, ast.Attribute) and ann.attr in TENANT_DEPS:
            return True
    # Also check for _safe_key_hash usage (legacy pattern — still acceptable)
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
            if child.func.id == "_safe_key_hash":
                return True
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            if child.func.attr == "_safe_key_hash":
                return True
    return False


def check_file(filepath: Path) -> list[dict]:
    """Check a single Python file for tenant isolation violations."""
    violations = []
    try:
        source = filepath.read_text()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue

        # Only check endpoint handlers (decorated with @app.get/post/etc or @router.get/post/etc)
        routes = _get_endpoint_decorators(node)
        if not routes:
            continue

        # Skip exempt functions
        if node.name in EXEMPT_FUNCTIONS:
            continue

        # Check if function references any tenant-scoped collection
        refs = _references_collection(node, TENANT_COLLECTIONS)
        if not refs:
            continue

        # Check if function has tenant scoping
        if _has_tenant_dep(node):
            continue

        violations.append({
            "file": str(filepath),
            "line": node.lineno,
            "function": node.name,
            "collections": sorted(refs),
        })

    return violations


def main():
    strict = "--strict" in sys.argv
    root = Path(__file__).parent.parent

    files_to_check = [
        root / "api" / "main.py",
        *(root / "api" / "routers").glob("*.py"),
    ]

    all_violations = []
    for filepath in files_to_check:
        if filepath.exists():
            all_violations.extend(check_file(filepath))

    if not all_violations:
        print("tenant-isolation-check: PASS (no violations found)")
        sys.exit(0)

    print(f"tenant-isolation-check: {'FAIL' if strict else 'WARN'} ({len(all_violations)} violations)")
    print()
    for v in all_violations:
        collections = ", ".join(v["collections"])
        print(f"  {v['file']}:{v['line']} — {v['function']}() accesses [{collections}] without TenantContext")
    print()
    if strict:
        print("Run with no flags for warn-only mode, or fix the violations above.")
        sys.exit(1)
    else:
        print("Warn-only mode. Run with --strict to fail the build.")
        # TODO(2026-05-01): Switch to --strict by default. See module docstring.
        sys.exit(0)


if __name__ == "__main__":
    main()
