#!/usr/bin/env python3
"""Analyze which detection layers fire first across synthetic scenarios.

This script uses synthetic data to model the ordering of detection layer
activations (Round 6-9) and reports which layers tend to trigger earliest.

Usage:
    python scripts/analyze_detection_ordering.py
"""
import os
import sys
from collections import Counter, defaultdict
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Detection layer names matching api/detection.py
DETECTION_LAYERS = [
    "timestamp_integrity",   # Round 6
    "identity_drift",        # Round 7
    "consensus_collapse",    # Round 8
    "provenance_chain",      # Round 9
]


def analyze_ordering(scenarios: list[dict]) -> dict:
    """Analyze detection layer firing order from scenario results.

    Each scenario should be a dict with:
        - id: str
        - layers_fired: list[str] — ordered list of layers that fired

    Returns analysis dict with first_fire_counts, co_occurrence, and ordering stats.
    """
    if not scenarios:
        return {"first_fire_counts": {}, "co_occurrence": {}, "total_scenarios": 0}

    first_fire = Counter()
    layer_counts = Counter()
    co_occurrence: dict[str, Counter] = defaultdict(Counter)

    for sc in scenarios:
        fired = sc.get("layers_fired", [])
        if not fired:
            continue

        # Count which layer fires first
        first_fire[fired[0]] += 1

        # Count total firings
        for layer in fired:
            layer_counts[layer] += 1

        # Co-occurrence: which layers fire together
        for i, la in enumerate(fired):
            for lb in fired[i + 1:]:
                co_occurrence[la][lb] += 1
                co_occurrence[lb][la] += 1

    return {
        "first_fire_counts": dict(first_fire.most_common()),
        "layer_total_counts": dict(layer_counts.most_common()),
        "co_occurrence": {k: dict(v) for k, v in co_occurrence.items()},
        "total_scenarios": len(scenarios),
    }


def generate_synthetic_scenarios(n: int = 100) -> list[dict]:
    """Generate synthetic detection scenarios for analysis.

    Simulates realistic patterns where:
    - timestamp_integrity fires most often (content-age mismatches are common)
    - identity_drift fires with authority expansion patterns
    - consensus_collapse fires with federation issues
    - provenance_chain fires with circular references
    """
    import random
    random.seed(42)

    scenarios = []
    for i in range(n):
        fired = []
        # Timestamp integrity fires ~60% of the time
        if random.random() < 0.6:
            fired.append("timestamp_integrity")
        # Identity drift fires ~30%
        if random.random() < 0.3:
            fired.append("identity_drift")
        # Consensus collapse fires ~20%
        if random.random() < 0.2:
            fired.append("consensus_collapse")
        # Provenance chain fires ~15%
        if random.random() < 0.15:
            fired.append("provenance_chain")

        scenarios.append({"id": f"scenario_{i}", "layers_fired": fired})

    return scenarios


if __name__ == "__main__":
    scenarios = generate_synthetic_scenarios(200)
    analysis = analyze_ordering(scenarios)

    print("=== Detection Layer Ordering Analysis ===")
    print(f"Total scenarios: {analysis['total_scenarios']}")
    print()
    print("First-fire frequency:")
    for layer, count in analysis["first_fire_counts"].items():
        pct = count / analysis["total_scenarios"] * 100
        print(f"  {layer}: {count} ({pct:.1f}%)")
    print()
    print("Total layer activations:")
    for layer, count in analysis.get("layer_total_counts", {}).items():
        print(f"  {layer}: {count}")
