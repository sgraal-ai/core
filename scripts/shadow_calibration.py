"""
Shadow calibration stub for Sgraal Ω_MEM weights.

Reads closed outcomes from Supabase outcome_log, counts component
attribution frequencies, and prints suggested β weight adjustments.

Real PyMC-based Bayesian calibration will replace this stub after
50+ closed outcomes are collected.

Usage:
    SUPABASE_URL=... SUPABASE_KEY=... python scripts/shadow_calibration.py
"""

import os
import sys
from collections import Counter

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Current β weights from omega_mem.py
CURRENT_WEIGHTS = {
    "s_freshness":    0.15,
    "s_drift":        0.15,
    "s_provenance":   0.12,
    "s_propagation":  0.12,
    "r_recall":       0.18,
    "r_encode":       0.12,
    "s_interference": 0.10,
    "s_recovery":    -0.10,
    "r_belief":       0.05,
    "s_relevance":    0.06,
}

# Adjustment step per attribution (stub: simple frequency-based bump)
ADJUSTMENT_STEP = 0.005


def fetch_closed_outcomes():
    """Fetch all closed (non-open) outcomes from Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_KEY required.")
        sys.exit(1)

    from supabase import create_client
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    result = (
        client.table("outcome_log")
        .select("outcome_id, status, component_attribution")
        .neq("status", "open")
        .execute()
    )
    return result.data


def compute_attribution_frequencies(outcomes):
    """Count how often each component is attributed to failures."""
    counter = Counter()
    failure_count = 0

    for outcome in outcomes:
        if outcome["status"] in ("failure", "partial"):
            failure_count += 1
            for component in (outcome.get("component_attribution") or []):
                counter[component] += 1

    return counter, failure_count


def suggest_adjustments(counter, failure_count):
    """Print suggested β weight adjustments based on attribution frequencies."""
    print(f"\n{'='*60}")
    print(f"Shadow Calibration Report")
    print(f"{'='*60}")
    print(f"Total closed outcomes: {len(outcomes)}")
    print(f"Failures/partial: {failure_count}")
    print()

    if failure_count < 10:
        print(f"Insufficient data ({failure_count} failures). Need 50+ for calibration.")
        print("Stub mode: printing raw frequencies only.\n")

    if not counter:
        print("No component attributions found.")
        return

    print(f"{'Component':<20} {'Attributions':>12} {'Current β':>10} {'Suggested β':>12}")
    print(f"{'-'*20} {'-'*12} {'-'*10} {'-'*12}")

    for component, count in counter.most_common():
        current = CURRENT_WEIGHTS.get(component, 0.0)
        # Stub: bump weight proportional to attribution frequency
        adjustment = count * ADJUSTMENT_STEP
        suggested = round(current + adjustment, 4)

        print(f"{component:<20} {count:>12} {current:>10.4f} {suggested:>12.4f}")

    print(f"\nNote: These are stub suggestions. Real PyMC calibration")
    print(f"will be implemented after 50+ outcomes are collected.")


if __name__ == "__main__":
    outcomes = fetch_closed_outcomes()
    counter, failure_count = compute_attribution_frequencies(outcomes)
    suggest_adjustments(counter, failure_count)
