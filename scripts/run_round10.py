"""Round 10 benchmark corpus runner.

Runs `round10_corpus.json` through `/v1/preflight` using FastAPI TestClient
and computes strict + lenient F1, per-vector breakdown, detection layer fire
rate, and failure diagnostics. Writes results to
`research/results/round10_results.json`.

READ-ONLY on scoring logic. Does not modify any core .py files.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from statistics import mean
from typing import Any

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

CORPUS_PATH = "/Users/zsobrakpeter/core/tests/corpus/round10/round10_corpus.json"
RESULTS_PATH = "/Users/zsobrakpeter/core/research/results/round10_results.json"

DETECTION_LAYERS = (
    "timestamp_integrity",
    "identity_drift",
    "consensus_collapse",
    "provenance_chain_integrity",
)


def _load_corpus(path: str) -> dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "memory_state": case["memory_state"],
        "action_type": case["action_type"],
        "domain": case["domain"],
        "dry_run": True,
    }
    resp = client.post("/v1/preflight", headers=AUTH, json=payload)
    if resp.status_code != 200:
        return {
            "status_code": resp.status_code,
            "error": resp.text[:500],
            "decision": "ERROR",
            "omega": None,
            "layers_fired": [],
        }
    body = resp.json()
    layers_fired = []
    for layer in DETECTION_LAYERS:
        val = body.get(layer)
        if val == "MANIPULATED":
            layers_fired.append(layer)
    return {
        "status_code": 200,
        "decision": body.get("recommended_action", "UNKNOWN"),
        "omega": body.get("omega_mem_final"),
        "layers_fired": layers_fired,
        "raw_layer_values": {layer: body.get(layer) for layer in DETECTION_LAYERS},
    }


def _f1(tp: int, fn: int, fp: int = 0) -> float:
    # Per the task spec: precision = 1.0 (no negatives), recall = TP / (TP+FN)
    if tp + fn == 0:
        return 0.0
    precision = 1.0 if (tp + fp) == 0 else tp / (tp + fp)
    recall = tp / (tp + fn)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def main() -> int:
    corpus = _load_corpus(CORPUS_PATH)
    cases = corpus["cases"]
    n = len(cases)
    print(f"Loaded {n} cases from round10 corpus")

    # Per-case raw results
    results = []
    # Metric counters (overall)
    strict_tp_block = 0
    strict_partial_ask_user = 0
    strict_partial_warn = 0
    fn_use_memory = 0
    error_count = 0
    lenient_tp = 0

    # Per-vector
    by_vector_raw: dict[str, list[dict[str, Any]]] = defaultdict(list)
    # Detection layer fire counts
    layer_fire_counts = Counter()
    # Mean omega by vector
    omegas_by_vector: dict[str, list[float]] = defaultdict(list)
    # Failures (USE_MEMORY when expected BLOCK)
    failures = []

    for i, case in enumerate(cases, 1):
        out = _run_case(case)
        decision = out["decision"]
        omega = out["omega"]
        layers = out["layers_fired"]
        vector = case["attack_vector"]

        entry = {
            "case_id": case["case_id"],
            "vector": vector,
            "domain": case["domain"],
            "expected": case["expected_decision"],
            "decision": decision,
            "omega": omega,
            "layers_fired": layers,
        }
        results.append(entry)
        by_vector_raw[vector].append(entry)

        if out["status_code"] != 200:
            error_count += 1
            continue

        for layer in layers:
            layer_fire_counts[layer] += 1

        if omega is not None:
            omegas_by_vector[vector].append(float(omega))

        # Strict
        if decision == "BLOCK":
            strict_tp_block += 1
        elif decision == "ASK_USER":
            strict_partial_ask_user += 1
        elif decision == "WARN":
            strict_partial_warn += 1
        elif decision == "USE_MEMORY":
            fn_use_memory += 1
            failures.append({
                "case_id": case["case_id"],
                "omega": omega,
                "decision": decision,
                "expected": case["expected_decision"],
                "domain": case["domain"],
                "vector": vector,
                "layers_fired": layers,
                "attack_description": case.get("attack_description", ""),
                "miss_reason": _diagnose_miss(omega, layers, case),
            })

        # Lenient: any non-USE_MEMORY counts
        if decision != "USE_MEMORY":
            lenient_tp += 1

        if i % 20 == 0:
            print(f"  ...processed {i}/{n}  "
                  f"(block={strict_tp_block}, ask={strict_partial_ask_user}, "
                  f"warn={strict_partial_warn}, use_mem={fn_use_memory}, err={error_count})")

    # Metrics
    strict_f1 = _f1(tp=strict_tp_block, fn=(strict_partial_ask_user + strict_partial_warn + fn_use_memory + error_count))
    lenient_f1 = _f1(tp=lenient_tp, fn=(fn_use_memory + error_count))

    detection_rate_block_only = strict_tp_block / n if n else 0.0
    lenient_detection_rate = lenient_tp / n if n else 0.0

    # Per-vector
    by_vector = {}
    for vector, entries in by_vector_raw.items():
        v_n = len(entries)
        v_block = sum(1 for e in entries if e["decision"] == "BLOCK")
        v_ask = sum(1 for e in entries if e["decision"] == "ASK_USER")
        v_warn = sum(1 for e in entries if e["decision"] == "WARN")
        v_use = sum(1 for e in entries if e["decision"] == "USE_MEMORY")
        v_err = sum(1 for e in entries if e["decision"] == "ERROR")
        v_strict_f1 = _f1(tp=v_block, fn=(v_ask + v_warn + v_use + v_err))
        v_lenient_tp = sum(1 for e in entries if e["decision"] not in ("USE_MEMORY", "ERROR"))
        v_lenient_f1 = _f1(tp=v_lenient_tp, fn=(v_use + v_err))
        by_vector[vector] = {
            "n_cases": v_n,
            "block": v_block,
            "ask_user": v_ask,
            "warn": v_warn,
            "use_memory": v_use,
            "error": v_err,
            "strict_detection_rate": v_block / v_n if v_n else 0.0,
            "lenient_detection_rate": v_lenient_tp / v_n if v_n else 0.0,
            "strict_f1": v_strict_f1,
            "lenient_f1": v_lenient_f1,
        }

    detection_layer_fire_rate = {
        layer: layer_fire_counts[layer] / n if n else 0.0
        for layer in DETECTION_LAYERS
    }

    mean_omega_per_vector = {
        vector: (mean(vals) if vals else None)
        for vector, vals in omegas_by_vector.items()
    }

    # Summary paragraph
    summary = (
        f"Round 10 ran {n} cases (all BLOCK-expected attacks). "
        f"Strict (BLOCK-only) detection rate: {detection_rate_block_only:.3f} "
        f"(F1={strict_f1:.3f}). Lenient (BLOCK+ASK_USER+WARN) detection rate: "
        f"{lenient_detection_rate:.3f} (F1={lenient_f1:.3f}). "
        f"Missed (USE_MEMORY) cases: {fn_use_memory}. Errors: {error_count}. "
        f"Per-vector strict F1 — "
        f"adaptive_provenance_layering: {by_vector.get('adaptive_provenance_layering', {}).get('strict_f1', 0):.3f}, "
        f"silent_consensus_collapse_hard: {by_vector.get('silent_consensus_collapse_hard', {}).get('strict_f1', 0):.3f}."
    )

    output = {
        "corpus_round": 10,
        "n_cases": n,
        "metrics": {
            "strict": {
                "tp_block": strict_tp_block,
                "partial_ask_user": strict_partial_ask_user,
                "partial_warn": strict_partial_warn,
                "fn_use_memory": fn_use_memory,
                "errors": error_count,
                "detection_rate_block_only": detection_rate_block_only,
                "f1": strict_f1,
            },
            "lenient": {
                "tp_any_nonuse": lenient_tp,
                "fn_use_memory": fn_use_memory,
                "errors": error_count,
                "detection_rate": lenient_detection_rate,
                "f1": lenient_f1,
            },
        },
        "by_vector": by_vector,
        "detection_layer_fire_rate": detection_layer_fire_rate,
        "mean_omega_per_vector": mean_omega_per_vector,
        "failures": failures,
        "summary": summary,
    }

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWrote results to {RESULTS_PATH}")
    print(f"\n=== Summary ===\n{summary}")

    # Print top 3 failures
    if failures:
        print(f"\n=== Top {min(3, len(failures))} failures ===")
        for fail in failures[:3]:
            print(f"  {fail['case_id']} [{fail['vector']}/{fail['domain']}] "
                  f"omega={fail['omega']}, layers={fail['layers_fired']}")
            print(f"    reason: {fail['miss_reason']}")
            print(f"    attack: {fail['attack_description'][:120]}")

    return 0


def _diagnose_miss(omega: float | None, layers: list[str], case: dict[str, Any]) -> str:
    reasons = []
    if omega is None:
        return "no omega returned (error path)"
    if not layers:
        reasons.append("no detection layer fired")
    if omega < 70:
        reasons.append(f"omega={omega:.1f} below BLOCK threshold (70)")
    mem_trusts = [e.get("source_trust", 0) for e in case["memory_state"]]
    mean_trust = mean(mem_trusts) if mem_trusts else 0
    if mean_trust > 0.7:
        reasons.append(f"high mean source_trust={mean_trust:.2f}")
    mem_conflicts = [e.get("source_conflict", 0) for e in case["memory_state"]]
    mean_conflict = mean(mem_conflicts) if mem_conflicts else 0
    if mean_conflict < 0.3:
        reasons.append(f"low mean source_conflict={mean_conflict:.2f}")
    return "; ".join(reasons) or "unclear miss"


if __name__ == "__main__":
    sys.exit(main())
