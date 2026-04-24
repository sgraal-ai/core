#!/usr/bin/env python3
"""Analyze per-tenant churn risk based on call frequency trends.

This script reads from the /v1/analytics endpoints via TestClient
and computes per-tenant call frequency trends to identify tenants
whose usage is declining (potential churn).

Usage:
    python scripts/analyze_churn_risk.py
"""
import os
import sys
import math
from collections import defaultdict
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def compute_churn_risk(call_history: list[dict]) -> dict:
    """Compute churn risk from a list of call records.

    Each record should have at minimum:
        - tenant: str
        - timestamp: float (epoch seconds)

    Returns dict mapping tenant -> {risk_score, trend, calls_recent, calls_older}.
    """
    if not call_history:
        return {}

    # Group by tenant
    by_tenant: dict[str, list[float]] = defaultdict(list)
    for rec in call_history:
        tenant = rec.get("tenant", "unknown")
        ts = rec.get("timestamp", 0)
        by_tenant[tenant].append(float(ts))

    results = {}
    for tenant, timestamps in by_tenant.items():
        timestamps.sort()
        if len(timestamps) < 2:
            results[tenant] = {
                "risk_score": 0.0,
                "trend": "insufficient_data",
                "calls_recent": len(timestamps),
                "calls_older": 0,
            }
            continue

        # Split into two halves: older vs recent
        mid = len(timestamps) // 2
        older = timestamps[:mid]
        recent = timestamps[mid:]

        # Compute average interval in each half
        older_span = (older[-1] - older[0]) if len(older) > 1 else 1.0
        recent_span = (recent[-1] - recent[0]) if len(recent) > 1 else 1.0

        older_rate = len(older) / max(older_span, 1.0)
        recent_rate = len(recent) / max(recent_span, 1.0)

        # Risk: ratio of decline
        if older_rate > 0:
            ratio = recent_rate / older_rate
        else:
            ratio = 1.0

        # Score: 0 = no risk, 1 = high risk
        if ratio >= 1.0:
            risk_score = 0.0
            trend = "growing"
        elif ratio >= 0.5:
            risk_score = round(1.0 - ratio, 3)
            trend = "declining"
        else:
            risk_score = round(min(1.0, 1.0 - ratio), 3)
            trend = "high_churn_risk"

        results[tenant] = {
            "risk_score": risk_score,
            "trend": trend,
            "calls_recent": len(recent),
            "calls_older": len(older),
        }

    return results


def rank_by_risk(churn_results: dict) -> list[tuple[str, dict]]:
    """Return tenants sorted by churn risk (highest first)."""
    return sorted(churn_results.items(), key=lambda x: x[1]["risk_score"], reverse=True)


if __name__ == "__main__":
    # Example with synthetic data
    import time

    now = time.time()
    synthetic = []
    # Tenant A: steady usage
    for i in range(100):
        synthetic.append({"tenant": "tenant_a", "timestamp": now - i * 3600})
    # Tenant B: declining usage (fewer recent calls)
    for i in range(80):
        synthetic.append({"tenant": "tenant_b", "timestamp": now - 86400 * 30 + i * 3600})
    for i in range(5):
        synthetic.append({"tenant": "tenant_b", "timestamp": now - i * 86400})

    results = compute_churn_risk(synthetic)
    ranked = rank_by_risk(results)

    print("=== Churn Risk Analysis ===")
    for tenant, info in ranked:
        print(f"  {tenant}: risk={info['risk_score']:.3f} trend={info['trend']} "
              f"(recent={info['calls_recent']}, older={info['calls_older']})")
