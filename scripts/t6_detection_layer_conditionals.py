"""T6 — Detection Layer Conditional Probabilities.

Compute 4x4 conditional matrix P(layer_B fires | layer_A fires).
Reuses per-block hits cached by T4 if available; otherwise re-runs corpus.

Writes: /Users/zsobrakpeter/core/research/results/detection_layer_conditionals.json
"""
import os
import sys
import json

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")

LAYERS = [
    "timestamp_integrity",
    "identity_drift",
    "consensus_collapse",
    "provenance_chain_integrity",
]

OUTPUT = "/Users/zsobrakpeter/core/research/results/detection_layer_conditionals.json"
CACHE = "/Users/zsobrakpeter/core/research/results/.t4_per_block_hits.json"


def _collect_hits():
    """Return list of dicts {layer: bool} for each BLOCK case."""
    if os.path.exists(CACHE):
        with open(CACHE) as f:
            hits = json.load(f)
        print(f"Loaded {len(hits)} per-block hits from T4 cache")
        return hits
    # Fallback: re-run corpus
    from fastapi.testclient import TestClient
    from api.main import app, _load_benchmark_corpus
    client = TestClient(app)
    AUTH = {"Authorization": "Bearer sg_test_key_001"}
    cases = _load_benchmark_corpus()
    print(f"No T4 cache — re-running {len(cases)} cases")
    hits = []
    for i, case in enumerate(cases):
        payload = {
            "memory_state": case["memory_state"],
            "action_type": case.get("action_type", "reversible"),
            "domain": case.get("domain", "general"),
        }
        try:
            r = client.post("/v1/preflight", json=payload, headers=AUTH)
            if r.status_code != 200:
                continue
            data = r.json()
        except Exception:
            continue
        if data.get("recommended_action") == "BLOCK":
            hits.append({l: data.get(l) == "MANIPULATED" for l in LAYERS})
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(cases)}")
    return hits


def main():
    hits = _collect_hits()
    n = len(hits)
    print(f"Computing conditional matrix over {n} BLOCK cases")

    # Marginals: count(layer fired)
    marginals = {layer: sum(1 for h in hits if h[layer]) for layer in LAYERS}

    # Joint: count(A AND B)
    joints = {}
    for a in LAYERS:
        joints[a] = {}
        for b in LAYERS:
            joints[a][b] = sum(1 for h in hits if h[a] and h[b])

    # Conditional P(B | A) = P(A AND B) / P(A)
    conditional = {}
    for a in LAYERS:
        conditional[a] = {}
        for b in LAYERS:
            if marginals[a] > 0:
                conditional[a][b] = round(joints[a][b] / marginals[a], 4)
            else:
                conditional[a][b] = None  # Undefined

    # Find most & least correlated pairs (exclude diagonals)
    off_diag = []
    for a in LAYERS:
        for b in LAYERS:
            if a == b:
                continue
            v = conditional[a][b]
            if v is None:
                continue
            off_diag.append((a, b, v))
    off_diag.sort(key=lambda t: t[2], reverse=True)
    most = off_diag[0] if off_diag else (None, None, None)
    least = off_diag[-1] if off_diag else (None, None, None)

    # Attack fingerprint: describe dominant co-firing pattern
    # Find the pair A,B where both P(B|A) and P(A|B) are high — symmetric co-firing
    symmetric = []
    for a in LAYERS:
        for b in LAYERS:
            if a >= b:
                continue
            if conditional[a][b] is None or conditional[b][a] is None:
                continue
            sym = (conditional[a][b] + conditional[b][a]) / 2
            symmetric.append((a, b, sym))
    symmetric.sort(key=lambda t: t[2], reverse=True)
    top = symmetric[0] if symmetric else (None, None, 0)

    if top[2] > 0.8:
        fingerprint = f"Dominant co-firing: {top[0]} <-> {top[1]} (symmetric P={top[2]:.2f}) — these layers often fire together, likely addressing same attack vectors."
    elif top[2] > 0.5:
        fingerprint = f"Moderate co-firing between {top[0]} and {top[1]} (P={top[2]:.2f}) — partial overlap."
    else:
        fingerprint = "Layers fire largely independently — each targets distinct attack classes."

    result = {
        "layers": LAYERS,
        "n_block_cases": n,
        "marginals": marginals,
        "conditional_matrix": conditional,
        "independence_test": {
            "pair_most_correlated": [most[0], most[1], most[2]] if most[0] else None,
            "pair_least_correlated": [least[0], least[1], least[2]] if least[0] else None,
        },
        "attack_fingerprint": fingerprint,
    }

    with open(OUTPUT, "w") as f:
        json.dump(result, f, indent=2)

    print("\n=== T6 RESULTS ===")
    print(json.dumps(result, indent=2))
    print(f"\nWrote {OUTPUT}")


if __name__ == "__main__":
    main()
