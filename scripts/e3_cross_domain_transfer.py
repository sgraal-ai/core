"""E3 — Cross-Domain Transfer Matrix.

Simulates synthetic attacks per domain, captures the component_breakdown
from /v1/preflight as a signature vector, and computes cosine similarity
between every domain pair. Higher similarity means an attack that works
in one domain transfers (is recognizable) in the other.

Output: /Users/zsobrakpeter/core/research/results/cross_domain_transfer.json
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

DOMAINS = ["general", "customer_support", "coding", "legal", "fintech", "medical"]
N_ATTACKS_PER_DOMAIN = 10
OUTPUT_PATH = Path("/Users/zsobrakpeter/core/research/results/cross_domain_transfer.json")

# Canonical 10-D component ordering (matches research corpus)
COMPONENTS = [
    "s_freshness",
    "s_drift",
    "s_provenance",
    "s_propagation",
    "r_recall",
    "r_encode",
    "s_interference",
    "s_recovery",
    "r_belief",
    "s_relevance",
]

ATTACK_VECTORS = ["stale_data", "poisoned_provenance", "consensus_collapse"]

# Domain flavoring — different payload characteristics shift the component mix,
# mimicking how real-world attacks have different texture per domain.
# Values: (age_multiplier, trust_bias, conflict_bias, downstream_bias, n_entries_bias)
DOMAIN_FLAVOR: dict[str, dict[str, float]] = {
    "general":          {"age_mul": 1.00, "trust_b": 0.00, "conflict_b": 0.00, "ds_b": 0, "n_bias": 0},
    "customer_support": {"age_mul": 0.70, "trust_b": 0.10, "conflict_b": -0.05, "ds_b": 2, "n_bias": 1},
    "coding":           {"age_mul": 1.20, "trust_b": -0.05, "conflict_b": 0.05, "ds_b": -1, "n_bias": 0},
    "legal":            {"age_mul": 1.80, "trust_b": 0.05, "conflict_b": 0.10, "ds_b": 1, "n_bias": 1},
    "fintech":          {"age_mul": 0.85, "trust_b": -0.10, "conflict_b": 0.15, "ds_b": 3, "n_bias": 2},
    "medical":          {"age_mul": 2.20, "trust_b": 0.02, "conflict_b": 0.12, "ds_b": 2, "n_bias": 2},
}


def _flav(domain: str) -> dict[str, float]:
    return DOMAIN_FLAVOR[domain]


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _stale_data_entries(seed: int, domain: str) -> list[dict[str, Any]]:
    """Stale but otherwise clean entries — triggers s_freshness / r_recall."""
    f = _flav(domain)
    base_age = (120 + (seed * 7) % 90) * f["age_mul"]
    n = 4 + int(f["n_bias"])
    return [
        {
            "id": f"stale-{domain}-{seed}-{i}",
            "content": f"{domain} reference record s{seed} idx{i} token{(seed + i * 3) % 11}",
            "type": "tool_state" if i % 2 == 0 else "semantic",
            "timestamp_age_days": int(base_age + i * 3),
            "source_trust": _clamp(0.85 + f["trust_b"] - (i * 0.03) - (seed % 5) * 0.01),
            "source_conflict": _clamp(0.05 + f["conflict_b"] + (seed % 3) * 0.02),
            "downstream_count": max(1, 2 + (i % 3) + int(f["ds_b"])),
        }
        for i in range(n)
    ]


def _poisoned_provenance_entries(seed: int, domain: str) -> list[dict[str, Any]]:
    """Low trust + high conflict — triggers s_provenance / s_interference."""
    f = _flav(domain)
    n = 5 + int(f["n_bias"])
    return [
        {
            "id": f"poison-{domain}-{seed}-{i}",
            "content": f"{domain} attested fact s{seed}-{i} token{(seed * 2 + i) % 13}",
            "type": "semantic" if i % 2 == 0 else "shared_workflow",
            "timestamp_age_days": int((20 + (seed * 5 % 30) + i) * f["age_mul"]),
            "source_trust": _clamp(0.22 + f["trust_b"] + (i * 0.05) - (seed % 4) * 0.02),
            "source_conflict": _clamp(
                0.55 + f["conflict_b"] + ((seed + i) % 7) * 0.04
            ),
            "downstream_count": max(1, 5 + (i * 2) + int(f["ds_b"])),
            "provenance": {
                "hops": 3 + (i % 2) + (1 if f["conflict_b"] > 0.1 else 0),
                "sources": [f"unverified-{i}", f"contested-{i}-{domain[:3]}"],
            },
        }
        for i in range(n)
    ]


def _consensus_collapse_entries(seed: int, domain: str) -> list[dict[str, Any]]:
    """Many near-duplicate entries with uniform trust — triggers s_propagation."""
    f = _flav(domain)
    shared_claim = f"{domain} policy claim C-{seed}"
    n = 6 + int(f["n_bias"])
    return [
        {
            "id": f"collapse-{domain}-{seed}-{i}",
            "content": shared_claim + (f" (restated v{i} token{(seed + i) % 9})" if i else ""),
            "type": "policy" if i == 0 else "shared_workflow",
            "timestamp_age_days": int((8 + i) * f["age_mul"]),
            "source_trust": _clamp(0.70 + f["trust_b"] - (i % 3) * 0.01),
            "source_conflict": _clamp(0.15 + f["conflict_b"] + (seed % 4) * 0.02),
            "downstream_count": max(1, 8 + i + int(f["ds_b"])),
            "provenance": {"hops": 2, "sources": [f"echo-agent-{i}-{domain[:3]}"]},
        }
        for i in range(n)
    ]


def build_attack(domain: str, vector: str, seed: int) -> dict[str, Any]:
    if vector == "stale_data":
        mem = _stale_data_entries(seed, domain)
        action = "irreversible"
    elif vector == "poisoned_provenance":
        mem = _poisoned_provenance_entries(seed, domain)
        action = "destructive"
    elif vector == "consensus_collapse":
        mem = _consensus_collapse_entries(seed, domain)
        action = "reversible"
    else:
        raise ValueError(vector)

    return {
        "agent_id": f"e3-{domain}-{vector}-{seed}",
        "action_type": action,
        "domain": domain,
        "memory_state": mem,
    }


def preflight(payload: dict[str, Any]) -> dict[str, Any] | None:
    try:
        r = client.post("/v1/preflight", headers=AUTH, json=payload, timeout=30)
    except Exception as exc:  # pragma: no cover - transport error
        print(f"  transport error: {exc}", file=sys.stderr)
        return None
    if r.status_code != 200:
        print(f"  non-200 ({r.status_code}): {r.text[:200]}", file=sys.stderr)
        return None
    return r.json()


def signature_from_breakdown(breakdown: dict[str, Any]) -> list[float]:
    """Map the component_breakdown dict to a canonical 10-D vector.

    Values in component_breakdown are typically dicts with a 'value' key
    (the per-component risk score), but may be plain floats. We coerce both.
    """
    vec: list[float] = []
    for key in COMPONENTS:
        item = breakdown.get(key, 0.0)
        if isinstance(item, dict):
            raw = item.get("value", item.get("score", 0.0))
        else:
            raw = item
        try:
            vec.append(float(raw))
        except (TypeError, ValueError):
            vec.append(0.0)
    return vec


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def mean_pairwise_cosine(sigs_a: list[list[float]], sigs_b: list[list[float]]) -> float:
    if not sigs_a or not sigs_b:
        return 0.0
    total = 0.0
    n = 0
    for va in sigs_a:
        for vb in sigs_b:
            total += cosine(va, vb)
            n += 1
    return total / n if n else 0.0


def collect_signatures() -> dict[str, list[list[float]]]:
    signatures: dict[str, list[list[float]]] = {d: [] for d in DOMAINS}
    for d_idx, domain in enumerate(DOMAINS):
        print(f"[collect] {domain} …")
        needed = N_ATTACKS_PER_DOMAIN
        seed = d_idx * 1000  # per-domain seed namespace
        vector_idx = 0
        guard = 0
        while len(signatures[domain]) < needed and guard < needed * 4:
            vector = ATTACK_VECTORS[vector_idx % len(ATTACK_VECTORS)]
            payload = build_attack(domain, vector, seed)
            resp = preflight(payload)
            seed += 1
            vector_idx += 1
            guard += 1
            if not resp:
                continue
            breakdown = resp.get("component_breakdown")
            if not isinstance(breakdown, dict) or not breakdown:
                continue
            sig = signature_from_breakdown(breakdown)
            if sum(abs(v) for v in sig) == 0.0:
                continue
            signatures[domain].append(sig)
        print(f"  collected {len(signatures[domain])} signatures")
    return signatures


def build_matrix(
    signatures: dict[str, list[list[float]]],
) -> dict[str, dict[str, float]]:
    matrix: dict[str, dict[str, float]] = {}
    for a in DOMAINS:
        matrix[a] = {}
        for b in DOMAINS:
            matrix[a][b] = round(mean_pairwise_cosine(signatures[a], signatures[b]), 4)
    return matrix


def main() -> int:
    start = time.time()
    signatures = collect_signatures()

    # Drop domains that failed to collect any signatures (avoid NaN matrix)
    missing = [d for d in DOMAINS if not signatures[d]]
    if missing:
        print(f"WARN: domains with no signatures: {missing}", file=sys.stderr)

    matrix = build_matrix(signatures)

    # Find highest/lowest off-diagonal pair
    highest = ("", "", -1.0)
    lowest = ("", "", 2.0)
    off_diag_values: list[float] = []
    for a in DOMAINS:
        for b in DOMAINS:
            if a == b:
                continue
            val = matrix[a][b]
            off_diag_values.append(val)
            if val > highest[2]:
                highest = (a, b, val)
            if val < lowest[2]:
                lowest = (a, b, val)

    mean_transfer = sum(off_diag_values) / len(off_diag_values) if off_diag_values else 0.0

    # Symmetry check
    max_asym = 0.0
    for i, a in enumerate(DOMAINS):
        for b in DOMAINS[i + 1 :]:
            max_asym = max(max_asym, abs(matrix[a][b] - matrix[b][a]))

    conclusion = (
        f"Mean off-diagonal transfer = {mean_transfer:.3f}. "
        f"Highest transfer: {highest[0]} ↔ {highest[1]} ({highest[2]:.3f}) — "
        f"attack signatures in these domains are near-interchangeable, so fleet "
        f"vaccination propagates signatures effectively between them. "
        f"Lowest transfer: {lowest[0]} ↔ {lowest[1]} ({lowest[2]:.3f}) — "
        f"attacks here are domain-specific and require per-domain signatures. "
        f"Matrix symmetry: max |M[a,b] - M[b,a]| = {max_asym:.4f} "
        f"({'symmetric as expected' if max_asym < 1e-6 else 'sampling noise breaks perfect symmetry'})."
    )

    output = {
        "domains": DOMAINS,
        "method": "cosine_similarity_of_preflight_component_vectors",
        "components": COMPONENTS,
        "attack_vectors": ATTACK_VECTORS,
        "n_attacks_per_domain": N_ATTACKS_PER_DOMAIN,
        "signatures_collected": {d: len(signatures[d]) for d in DOMAINS},
        "transfer_matrix": matrix,
        "highest_transfer_pair": [highest[0], highest[1]],
        "highest_transfer_value": round(highest[2], 4),
        "lowest_transfer_pair": [lowest[0], lowest[1]],
        "lowest_transfer_value": round(lowest[2], 4),
        "mean_transfer": round(mean_transfer, 4),
        "max_asymmetry": round(max_asym, 6),
        "conclusion": conclusion,
        "elapsed_seconds": round(time.time() - start, 2),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))

    print("\n=== CROSS-DOMAIN TRANSFER MATRIX ===")
    header = "              " + "  ".join(f"{d[:7]:>7}" for d in DOMAINS)
    print(header)
    for a in DOMAINS:
        row = f"{a[:12]:>12}  " + "  ".join(f"{matrix[a][b]:7.3f}" for b in DOMAINS)
        print(row)
    print()
    print(f"highest: {highest[0]} ↔ {highest[1]} = {highest[2]:.3f}")
    print(f"lowest:  {lowest[0]} ↔ {lowest[1]} = {lowest[2]:.3f}")
    print(f"mean:    {mean_transfer:.3f}")
    print(f"max |M[a,b] - M[b,a]|: {max_asym:.4f}")
    print(f"output:  {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
