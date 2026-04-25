"""Canonical decision severity ordering — single source of truth.

Used by security-monotone pipeline, plugin hooks, cost-asymmetry,
identity drift escalation, and other decision comparison logic.
DO NOT modify the ordering without updating all consumers.
"""

SEVERITY = {"USE_MEMORY": 0, "WARN": 1, "ASK_USER": 2, "BLOCK": 3}

SEVERITY_ORDER = ["USE_MEMORY", "WARN", "ASK_USER", "BLOCK"]


def compare_severity(a: str, b: str) -> int:
    """Compare two decisions by severity. Returns -1, 0, or 1.

    compare_severity("WARN", "BLOCK") → -1 (a is less severe)
    compare_severity("BLOCK", "WARN") → 1 (a is more severe)
    compare_severity("WARN", "WARN") → 0
    """
    sa = SEVERITY.get(a, 0)
    sb = SEVERITY.get(b, 0)
    return (sa > sb) - (sa < sb)
