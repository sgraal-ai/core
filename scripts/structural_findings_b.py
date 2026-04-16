"""
Structural Findings B
- TASK 7: Component correlation in raw 10D space (449 corpus cases)
- TASK 8: PCA reconstruction loss (top-5 eigen projection, correct vs error cases)
- TASK 9: Latency percentile distribution (1000 preflight calls)

Outputs merged into research/results/structural_findings.json
"""
from __future__ import annotations

import os
import sys
import json
import math
import time
import random
import statistics
from pathlib import Path

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")

from fastapi.testclient import TestClient
from api.main import app, _load_benchmark_corpus

import numpy as np

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

RESULTS_PATH = Path("/Users/zsobrakpeter/core/research/results/structural_findings.json")

RAW_COMPONENTS = [
    "s_freshness", "s_drift", "s_provenance", "s_propagation",
    "r_recall", "r_encode", "s_interference", "s_recovery",
    "r_belief", "s_relevance",
]

random.seed(42)
np.random.seed(42)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pearson(x, y):
    n = len(x)
    if n == 0:
        return 0.0
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    denx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    deny = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if denx * deny == 0:
        return 0.0
    return num / (denx * deny)


def _percentile(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    if p <= 0:
        return sorted_vals[0]
    if p >= 100:
        return sorted_vals[-1]
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def _load_existing():
    if RESULTS_PATH.exists():
        try:
            with open(RESULTS_PATH) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_merged(new_keys: dict):
    existing = _load_existing()
    existing.update(new_keys)
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(existing, f, indent=2)


# ---------------------------------------------------------------------------
# TASK 7 — Component Correlation
# ---------------------------------------------------------------------------

def task7_component_correlation():
    print("=" * 70)
    print("TASK 7 — Component Correlation in Raw 10D Space")
    print("=" * 70)

    cases = _load_benchmark_corpus()
    print(f"Loaded {len(cases)} corpus cases")

    matrix = []  # N x 10
    decisions_actual = []
    decisions_expected = []
    rounds = []

    t_start = time.perf_counter()
    for i, c in enumerate(cases):
        payload = {
            "memory_state": c["memory_state"],
            "action_type": c.get("action_type", "reversible"),
            "domain": c.get("domain", "general"),
        }
        try:
            r = client.post("/v1/preflight", headers=AUTH, json=payload)
            if r.status_code != 200:
                continue
            body = r.json()
            cb = body.get("component_breakdown", {}) or {}
            row = [float(cb.get(k, 0.0) or 0.0) for k in RAW_COMPONENTS]
            matrix.append(row)
            decisions_actual.append(body.get("recommended_action", "USE_MEMORY"))
            decisions_expected.append(c.get("expected_decision", "USE_MEMORY"))
            rounds.append(c.get("round"))
        except Exception as e:
            print(f"  error on case {i}: {e}")
        if (i + 1) % 50 == 0:
            print(f"  progress: {i + 1}/{len(cases)} ({time.perf_counter() - t_start:.1f}s)")

    N = len(matrix)
    print(f"Collected {N} rows")

    # Build 10x10 correlation matrix
    cols = list(zip(*matrix))  # 10 columns
    corr = [[0.0] * 10 for _ in range(10)]
    for i in range(10):
        for j in range(10):
            corr[i][j] = _pearson(list(cols[i]), list(cols[j]))

    # Top 5 correlated (> 0.7) and anti-correlated (< -0.3)
    pairs = []
    for i in range(10):
        for j in range(i + 1, 10):
            pairs.append((RAW_COMPONENTS[i], RAW_COMPONENTS[j], corr[i][j]))

    high_corr = sorted([p for p in pairs if p[2] > 0.7], key=lambda x: -x[2])[:5]
    anti_corr = sorted([p for p in pairs if p[2] < -0.3], key=lambda x: x[2])[:5]

    # Most independent components: mean abs corr with others
    mean_abs = {}
    for i in range(10):
        vals = [abs(corr[i][j]) for j in range(10) if j != i]
        mean_abs[RAW_COMPONENTS[i]] = sum(vals) / len(vals) if vals else 0.0
    independent = sorted(mean_abs.items(), key=lambda x: x[1])[:3]

    result = {
        "n_cases": N,
        "components": RAW_COMPONENTS,
        "correlation_matrix": {
            RAW_COMPONENTS[i]: {RAW_COMPONENTS[j]: round(corr[i][j], 4) for j in range(10)}
            for i in range(10)
        },
        "high_correlation_pairs_r_gt_0_7": [
            {"a": a, "b": b, "r": round(r_, 4)} for (a, b, r_) in high_corr
        ],
        "anti_correlation_pairs_r_lt_minus_0_3": [
            {"a": a, "b": b, "r": round(r_, 4)} for (a, b, r_) in anti_corr
        ],
        "most_independent_components_by_mean_abs_corr": [
            {"component": k, "mean_abs_corr": round(v, 4)} for k, v in independent
        ],
        "mean_abs_corr_all": {k: round(v, 4) for k, v in mean_abs.items()},
    }

    print(f"\n  N = {N} cases")
    print("\n  High correlation (r > 0.7):")
    for a, b, r_ in high_corr:
        print(f"    {a:20s} <-> {b:20s}  r = {r_:+.4f}")
    print("\n  Anti-correlation (r < -0.3):")
    for a, b, r_ in anti_corr:
        print(f"    {a:20s} <-> {b:20s}  r = {r_:+.4f}")
    print("\n  Most independent components:")
    for c, v in independent:
        print(f"    {c:20s}  mean |r| = {v:.4f}")

    # Preserve the matrix + decisions for TASK 8
    return result, matrix, decisions_actual, decisions_expected, rounds


# ---------------------------------------------------------------------------
# TASK 8 — PCA Reconstruction Loss
# ---------------------------------------------------------------------------

def task8_pca_reconstruction(matrix, decisions_actual, decisions_expected):
    print("\n" + "=" * 70)
    print("TASK 8 — PCA Reconstruction Loss (top-5 eigen projection)")
    print("=" * 70)

    X = np.array(matrix, dtype=float)
    N, D = X.shape
    print(f"  Shape: {N} x {D}")

    # Standardize (z-score). Guard against zero-variance columns.
    mean_ = X.mean(axis=0)
    std_ = X.std(axis=0, ddof=0)
    std_safe = np.where(std_ < 1e-12, 1.0, std_)
    X_std = (X - mean_) / std_safe

    # Covariance matrix (10 x 10) from standardized data
    cov = (X_std.T @ X_std) / max(N - 1, 1)

    # Symmetric eigendecomposition
    eigvals, eigvecs = np.linalg.eigh(cov)
    order = np.argsort(eigvals)[::-1]
    eigvals = eigvals[order]
    eigvecs = eigvecs[:, order]

    total_var = float(np.sum(eigvals))
    var_top5 = float(np.sum(eigvals[:5]))
    frac_top5 = var_top5 / total_var if total_var > 0 else 0.0
    frac_top5_pct = frac_top5 * 100

    # Project + reconstruct
    V5 = eigvecs[:, :5]
    X_proj = X_std @ V5
    X_recon = X_proj @ V5.T

    diff = X_std - X_recon
    # per-row reconstruction error (L2 norm)
    per_row_err = np.sqrt((diff ** 2).sum(axis=1))

    # per-component reconstruction error (RMSE across rows)
    per_col_err = np.sqrt((diff ** 2).mean(axis=0))

    # Classify correct vs error
    correct_mask = np.array([a == e for a, e in zip(decisions_actual, decisions_expected)])
    error_mask = ~correct_mask

    mean_correct = float(per_row_err[correct_mask].mean()) if correct_mask.any() else 0.0
    mean_error = float(per_row_err[error_mask].mean()) if error_mask.any() else 0.0
    ratio = (mean_error / mean_correct) if mean_correct > 0 else 0.0

    print(f"\n  Variance in top 5 eigenvalues: {frac_top5_pct:.2f}% (total var = {total_var:.4f})")
    print(f"  Eigenvalues: {[round(float(x), 4) for x in eigvals]}")
    print(f"\n  Correct cases: {int(correct_mask.sum())}")
    print(f"  Error cases:   {int(error_mask.sum())}")
    print(f"  Mean recon error (correct): {mean_correct:.4f}")
    print(f"  Mean recon error (error):   {mean_error:.4f}")
    print(f"  Ratio error/correct:        {ratio:.4f}  {'(concentrated in discarded variance: YES)' if ratio > 1.5 else '(NOT strongly concentrated)'}")

    per_col = sorted(
        [(RAW_COMPONENTS[i], float(per_col_err[i])) for i in range(D)],
        key=lambda x: -x[1],
    )
    print("\n  Per-component reconstruction error (RMSE, sorted desc):")
    for c, v in per_col:
        print(f"    {c:20s}  {v:.4f}")

    result = {
        "n_cases": int(N),
        "n_components_original": int(D),
        "n_components_kept": 5,
        "variance_fraction_top5": round(float(frac_top5), 6),
        "variance_percent_top5": round(float(frac_top5_pct), 4),
        "variance_discarded_percent": round(float(100.0 - frac_top5_pct), 4),
        "eigenvalues_desc": [round(float(x), 6) for x in eigvals],
        "eigenvalue_ratios_desc": [
            round(float(x) / total_var, 6) if total_var > 0 else 0.0 for x in eigvals
        ],
        "per_row_reconstruction_error": {
            "mean": round(float(per_row_err.mean()), 4),
            "std": round(float(per_row_err.std()), 4),
            "min": round(float(per_row_err.min()), 4),
            "max": round(float(per_row_err.max()), 4),
        },
        "correct_vs_error": {
            "n_correct": int(correct_mask.sum()),
            "n_error": int(error_mask.sum()),
            "mean_recon_error_correct": round(mean_correct, 6),
            "mean_recon_error_error": round(mean_error, 6),
            "ratio_error_over_correct": round(ratio, 6),
            "errors_concentrated_in_discarded_variance": bool(ratio > 1.5),
        },
        "per_component_reconstruction_error": [
            {"component": c, "rmse": round(v, 6)} for c, v in per_col
        ],
    }
    return result


# ---------------------------------------------------------------------------
# TASK 9 — Latency percentile distribution
# ---------------------------------------------------------------------------

def _mk_entry(i: int, age_days: float, trust: float, conflict: float, mtype: str):
    return {
        "id": f"e{i}",
        "content": f"memory entry {i} about topic {i % 10}",
        "type": mtype,
        "timestamp_age_days": float(age_days),
        "source_trust": float(trust),
        "source_conflict": float(conflict),
        "downstream_count": (i % 5),
    }


def _mk_payload(rng: random.Random):
    n = rng.choice([1, 2, 5, 10, 20])
    types = ["semantic", "episodic", "preference", "tool_state", "shared_workflow", "policy"]
    domain = rng.choice(["general", "customer_support", "coding", "legal", "fintech", "medical"])
    action_type = rng.choice(["informational", "reversible", "irreversible", "destructive"])

    entries = []
    for i in range(n):
        entries.append(_mk_entry(
            i=i,
            age_days=rng.uniform(0.0, 400.0),
            trust=rng.uniform(0.1, 0.99),
            conflict=rng.uniform(0.0, 0.8),
            mtype=rng.choice(types),
        ))

    # Include score_history sometimes to activate more modules
    score_history = None
    if rng.random() < 0.5:
        L = rng.choice([5, 10, 25, 50])
        score_history = [rng.uniform(10, 95) for _ in range(L)]

    payload = {
        "memory_state": entries,
        "action_type": action_type,
        "domain": domain,
    }
    if score_history is not None:
        payload["score_history"] = score_history
    return payload, n


def task9_latency():
    print("\n" + "=" * 70)
    print("TASK 9 — Latency percentile distribution (1000 calls)")
    print("=" * 70)

    rng = random.Random(1337)
    N = 1000
    samples = []  # (latency_ms, n_entries, early_exit, domain)

    # Warmup
    for _ in range(5):
        p, _ = _mk_payload(rng)
        client.post("/v1/preflight", headers=AUTH, json=p)

    t_start = time.perf_counter()
    for i in range(N):
        payload, n_entries = _mk_payload(rng)
        t0 = time.perf_counter()
        r = client.post("/v1/preflight", headers=AUTH, json=payload)
        t1 = time.perf_counter()
        latency_ms = (t1 - t0) * 1000.0
        early_exit = False
        if r.status_code == 200:
            try:
                body = r.json()
                early_exit = bool(body.get("early_exit", False))
            except Exception:
                pass
        samples.append((latency_ms, n_entries, early_exit, payload["domain"]))
        if (i + 1) % 100 == 0:
            print(f"  progress: {i + 1}/{N} ({time.perf_counter() - t_start:.1f}s)")

    latencies = [s[0] for s in samples]
    sorted_l = sorted(latencies)

    p50 = _percentile(sorted_l, 50)
    p75 = _percentile(sorted_l, 75)
    p90 = _percentile(sorted_l, 90)
    p95 = _percentile(sorted_l, 95)
    p99 = _percentile(sorted_l, 99)
    p999 = _percentile(sorted_l, 99.9)
    mn = sorted_l[0]
    mx = sorted_l[-1]
    mean_ = sum(latencies) / len(latencies)
    stddev = statistics.pstdev(latencies) if len(latencies) > 1 else 0.0

    # Outlier analysis (> p99)
    outliers = [s for s in samples if s[0] > p99]
    non_outliers = [s for s in samples if s[0] <= p99]

    # Correlation of latency vs n_entries
    lats = [s[0] for s in samples]
    ns = [s[1] for s in samples]
    corr_lat_n = _pearson(lats, ns)

    ee_rate_out = (sum(1 for s in outliers if s[2]) / len(outliers)) if outliers else 0.0
    ee_rate_non = (sum(1 for s in non_outliers if s[2]) / len(non_outliers)) if non_outliers else 0.0

    # Domain distribution among outliers
    dom_out = {}
    for s in outliers:
        dom_out[s[3]] = dom_out.get(s[3], 0) + 1
    dom_all = {}
    for s in samples:
        dom_all[s[3]] = dom_all.get(s[3], 0) + 1

    # Interpretation
    if corr_lat_n > 0.3 and ee_rate_out < ee_rate_non:
        interp = ("Outliers correlate with larger memory_state (more entries); "
                  "early_exit rate in outliers is lower. Outliers are the heavy-compute path (full module pipeline).")
    elif corr_lat_n > 0.3:
        interp = "Outliers correlate with larger memory_state; early_exit does not explain the difference."
    elif ee_rate_out < ee_rate_non:
        interp = "Outliers are concentrated in calls that did NOT early_exit (full pipeline path)."
    else:
        interp = "Outliers show no strong correlation with entry count or early_exit; likely jitter / cold-cache effects."

    print(f"\n  Samples: {len(latencies)}")
    print(f"  min      {mn:.3f} ms")
    print(f"  p50      {p50:.3f} ms")
    print(f"  p75      {p75:.3f} ms")
    print(f"  p90      {p90:.3f} ms")
    print(f"  p95      {p95:.3f} ms")
    print(f"  p99      {p99:.3f} ms")
    print(f"  p99.9    {p999:.3f} ms")
    print(f"  max      {mx:.3f} ms")
    print(f"  mean     {mean_:.3f} ms")
    print(f"  stddev   {stddev:.3f} ms")
    print(f"\n  Outliers (> p99): {len(outliers)}")
    print(f"  corr(latency, n_entries) = {corr_lat_n:.4f}")
    print(f"  early_exit rate in outliers:     {ee_rate_out:.3%}")
    print(f"  early_exit rate in non-outliers: {ee_rate_non:.3%}")
    print(f"  domain distribution (outliers): {dom_out}")
    print(f"  Interpretation: {interp}")

    return {
        "n_samples": len(latencies),
        "p50_ms": round(p50, 4),
        "p75_ms": round(p75, 4),
        "p90_ms": round(p90, 4),
        "p95_ms": round(p95, 4),
        "p99_ms": round(p99, 4),
        "p999_ms": round(p999, 4),
        "max_ms": round(mx, 4),
        "min_ms": round(mn, 4),
        "mean_ms": round(mean_, 4),
        "stddev_ms": round(stddev, 4),
        "outlier_analysis": {
            "n_outliers": len(outliers),
            "correlation_with_entries": round(corr_lat_n, 4),
            "early_exit_rate_in_outliers": round(ee_rate_out, 4),
            "early_exit_rate_in_non_outliers": round(ee_rate_non, 4),
            "outlier_domain_counts": dom_out,
            "overall_domain_counts": dom_all,
            "interpretation": interp,
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    t0 = time.perf_counter()

    task7_res, matrix, dec_a, dec_e, rounds = task7_component_correlation()
    task8_res = task8_pca_reconstruction(matrix, dec_a, dec_e)
    task9_res = task9_latency()

    new_keys = {
        "component_correlation": task7_res,
        "pca_reconstruction": task8_res,
        "latency_distribution": task9_res,
    }

    _save_merged(new_keys)
    elapsed = time.perf_counter() - t0
    print("\n" + "=" * 70)
    print(f"Saved merged results to {RESULTS_PATH}")
    print(f"Total time: {elapsed:.1f}s")
    print("=" * 70)


if __name__ == "__main__":
    main()
