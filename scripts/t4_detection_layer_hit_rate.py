"""T4 — Detection Layer Hit Rate Analysis.

For each BLOCK decision, count how many of the 4 detection layers fired
(field == "MANIPULATED"):
  - timestamp_integrity
  - identity_drift
  - consensus_collapse
  - provenance_chain_integrity

Writes: /Users/zsobrakpeter/core/research/results/detection_layer_analysis.json
"""
import os
import sys
import json
import statistics

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")

from fastapi.testclient import TestClient
from api.main import app, _load_benchmark_corpus

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

LAYERS = [
    "timestamp_integrity",
    "identity_drift",
    "consensus_collapse",
    "provenance_chain_integrity",
]

OUTPUT = "/Users/zsobrakpeter/core/research/results/detection_layer_analysis.json"


def main():
    cases = _load_benchmark_corpus()
    print(f"Loaded {len(cases)} corpus cases")

    n_total = 0
    n_blocks = 0
    distribution = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    per_layer_fires = {layer: 0 for layer in LAYERS}
    layers_per_block = []
    per_block_layer_hits = []  # list of dicts to reuse for T6

    errors = 0
    for i, case in enumerate(cases):
        payload = {
            "memory_state": case["memory_state"],
            "action_type": case.get("action_type", "reversible"),
            "domain": case.get("domain", "general"),
        }
        try:
            r = client.post("/v1/preflight", json=payload, headers=AUTH)
            if r.status_code != 200:
                errors += 1
                continue
            data = r.json()
        except Exception as e:
            errors += 1
            continue

        n_total += 1
        decision = data.get("recommended_action")
        layer_hits = {layer: data.get(layer) == "MANIPULATED" for layer in LAYERS}

        if decision == "BLOCK":
            n_blocks += 1
            fired = sum(layer_hits.values())
            distribution[fired] += 1
            layers_per_block.append(fired)
            for layer, hit in layer_hits.items():
                if hit:
                    per_layer_fires[layer] += 1
            per_block_layer_hits.append(layer_hits)

        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(cases)} processed — BLOCKs: {n_blocks}")

    mean_fired = statistics.mean(layers_per_block) if layers_per_block else 0.0
    median_fired = int(statistics.median(layers_per_block)) if layers_per_block else 0

    if mean_fired < 1.5:
        interpretation = "unique_work"
        recommendation = "Keep all 4 detection layers — each does unique work."
    elif mean_fired > 2.0:
        interpretation = "highly_redundant"
        recommendation = "Layers fire together frequently — skip 2-3 after first hit for speed."
    else:
        interpretation = "some_redundancy"
        recommendation = "Moderate overlap — consider early-exit after 2 layers fire."

    per_layer_rate = {
        layer: round(per_layer_fires[layer] / n_blocks, 4) if n_blocks else 0.0
        for layer in LAYERS
    }

    result = {
        "n_total_cases": n_total,
        "n_blocks": n_blocks,
        "distribution": {str(k): v for k, v in distribution.items()},
        "mean_layers_fired": round(mean_fired, 4),
        "median_layers_fired": median_fired,
        "interpretation": interpretation,
        "per_layer_fire_rate": per_layer_rate,
        "recommendation": recommendation,
        "errors": errors,
    }

    with open(OUTPUT, "w") as f:
        json.dump(result, f, indent=2)

    # Save the per-block hits to a temp file for T6 to reuse
    _cache = "/Users/zsobrakpeter/core/research/results/.t4_per_block_hits.json"
    with open(_cache, "w") as f:
        json.dump(per_block_layer_hits, f)

    print("\n=== T4 RESULTS ===")
    print(json.dumps(result, indent=2))
    print(f"\nWrote {OUTPUT}")


if __name__ == "__main__":
    main()
