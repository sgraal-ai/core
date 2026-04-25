#!/usr/bin/env python3
"""CI check: detect endpoints that access tenant-scoped collections without TenantContext.

Usage:
    python3 scripts/check_tenant_isolation.py [--strict]

Modes:
    Default (strict): exits 1 on any violation
    --warn-only: prints warnings but exits 0

    Hard-fail enabled 2026-04-25 after reaching 0 violations on both checks.
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
    "verify_passport",   # Public read-only: returns validity + hashed agent_id only, no tenant data
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
    strict = "--warn-only" not in sys.argv  # Default: strict (hard-fail)
    root = Path(__file__).parent.parent

    files_to_check = [
        root / "api" / "main.py",
        *(root / "api" / "routers").glob("*.py"),
    ]

    all_violations = []
    for filepath in files_to_check:
        if filepath.exists():
            all_violations.extend(check_file(filepath))

    _dict_failed = False
    if not all_violations:
        print("tenant-isolation-check: PASS (no violations found)")
    else:
        print(f"tenant-isolation-check: {'FAIL' if strict else 'WARN'} ({len(all_violations)} violations)")
        print()
        for v in all_violations:
            collections = ", ".join(v["collections"])
            print(f"  {v['file']}:{v['line']} — {v['function']}() accesses [{collections}] without TenantContext")
        print()
        if strict:
            _dict_failed = True


# ---------------------------------------------------------------------------
# Phase 2: Supabase query tenant isolation check
# ---------------------------------------------------------------------------

# Supabase tables that require tenant scoping (api_key_hash or api_key_id filter)
TENANT_SCOPED_TABLES = {
    "audit_log",       # must filter by api_key_id
    "api_keys",        # must filter by key_hash
    "aging_rules",     # must filter by api_key_hash
    "memory_store",    # must filter by api_key_hash
    "memory_versions", # must filter by api_key_hash
    "memory_ledger",   # must filter by entry_id + agent_id (composite)
    "outcome_log",     # must filter by api_key_id
    "team_members",    # must filter by team ownership
}

# Exemption marker: lines containing this comment skip the check
_SUPABASE_EXEMPT_MARKER = "CI_TENANT_SAFE"

# Functions exempt from Supabase tenant check (INSERT with tenant data, system-wide ops)
_SUPABASE_EXEMPT_FUNCTIONS = {
    "_scheduler_daily_snapshot",  # Scheduler: iterates per-tenant
    "_send_key_anomaly_email",   # Internal: scoped by customer_id
    "health",                    # Health check: exists query only
    "warmup",                    # Startup warmup: exists query only
    "destroy_entries",           # INSERT: includes api_key_id in record
    "production_validation",     # INSERT: includes api_key_id
    "generate_api_key",          # Signup: INSERT with key_hash
    "signup",                    # Signup: INSERT with key_hash
    "auth_register",             # Signup: scoped by email
    "_audit_log_sync",           # Internal: INSERT with api_key_id
    "heal",                      # Healing: INSERT with api_key_id
    "close_outcome",             # Outcome: INSERT with api_key_id
    "_preflight_internal",       # Preflight: uses _pf_tenant directly
}


def _check_supabase_tenant(filepath: Path) -> list[dict]:
    """Check Supabase queries for missing tenant filters."""
    violations = []
    try:
        lines = filepath.read_text().splitlines()
    except (UnicodeDecodeError, FileNotFoundError):
        return []

    import re as _sb_re

    # Build function-line map: for each line, find enclosing function name
    _current_func = ""
    _func_map: dict[int, str] = {}
    for li, ln in enumerate(lines, 1):
        _fn_match = _sb_re.match(r'^(?:async\s+)?def\s+(\w+)', ln)
        if _fn_match:
            _current_func = _fn_match.group(1)
        _func_map[li] = _current_func

    for i, line in enumerate(lines, 1):
        # Skip exempted lines
        if _SUPABASE_EXEMPT_MARKER in line:
            continue

        # Skip exempt functions
        if _func_map.get(i, "") in _SUPABASE_EXEMPT_FUNCTIONS:
            continue

        # Detect .table("X") pattern
        match = _sb_re.search(r'\.table\(["\'](\w+)["\']\)', line)
        if not match:
            continue

        table_name = match.group(1)
        if table_name not in TENANT_SCOPED_TABLES:
            continue

        # Check if this line or nearby lines (within 3 lines) have a tenant filter
        context = "\n".join(lines[max(0, i-2):min(len(lines), i+3)])
        has_filter = (
            'eq("api_key_hash"' in context or
            'eq("api_key_id"' in context or
            'eq("key_hash"' in context or
            ".eq(\"api_key_hash\"" in context or
            ".eq(\"api_key_id\"" in context or
            ".eq(\"key_hash\"" in context or
            _SUPABASE_EXEMPT_MARKER in context
        )

        if not has_filter:
            violations.append({
                "file": str(filepath),
                "line": i,
                "table": table_name,
                "code": line.strip()[:120],
            })

    return violations


def check_supabase():
    """Run Supabase tenant isolation check. Returns list of violations."""
    root = Path(__file__).parent.parent
    files_to_check = [
        root / "api" / "main.py",
        *(root / "api" / "routers").glob("*.py"),
    ]

    all_violations = []
    for filepath in files_to_check:
        if filepath.exists():
            all_violations.extend(_check_supabase_tenant(filepath))

    return all_violations


def main_supabase():
    """Entry point for Supabase-only check."""
    violations = check_supabase()
    if not violations:
        print("supabase-tenant-check: PASS (no violations found)")
        return

    print(f"supabase-tenant-check: WARN ({len(violations)} violations)")
    print()
    for v in violations:
        print(f"  {v['file']}:{v['line']} — table '{v['table']}' accessed without tenant filter")
        print(f"    {v['code']}")
    print()
    print("Add .eq('api_key_hash', kh) or .eq('api_key_id', kh) to fix.")
    print("Or add '# CI_TENANT_SAFE: <reason>' to exempt.")


if __name__ == "__main__":
    main()  # Sets _dict_failed via nonlocal — but we can't access it. Run both inline.
    # Re-run both checks together for combined exit code
    strict = "--warn-only" not in sys.argv
    root = Path(__file__).parent.parent
    files = [root / "api" / "main.py", *(root / "api" / "routers").glob("*.py")]

    dict_violations = []
    for fp in files:
        if fp.exists():
            dict_violations.extend(check_file(fp))

    sb_violations = check_supabase()

    print()
    if not sb_violations:
        print("supabase-tenant-check: PASS (no violations found)")
    else:
        print(f"supabase-tenant-check: {'FAIL' if strict else 'WARN'} ({len(sb_violations)} violations)")
        for v in sb_violations:
            print(f"  {v['file']}:{v['line']} — table '{v['table']}' without tenant filter")

    if strict and (dict_violations or sb_violations):
        sys.exit(1)
    elif not dict_violations and not sb_violations:
        sys.exit(0)
    else:
        sys.exit(0)
