"""Benchmark HMM optimization.

Measures post-optimization latency of:
  1. Direct compute_hmm_regime() calls (module-level)
  2. End-to-end /v1/preflight with score_history (full pipeline)

Reports p50/p99 and compares against the pre-optimization baseline from
research/results/module_latency_profile.json:
  - HMM module mean: 55.592 ms
  - End-to-end preflight mean: 17.683 ms

Run:
    python3 scripts/bench_hmm_optimization.py
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
from pathlib import Path

os.environ.setdefault("SGRAAL_SKIP_DNS_CHECK", "1")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scoring_engine.hmm import compute_hmm_regime, _clear_hmm_cache  # noqa: E402

BASELINE_PATH = ROOT / "research" / "results" / "module_latency_profile.json"


def percentile(xs, p):
    xs = sorted(xs)
    if not xs:
        return 0.0
    k = (len(xs) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    frac = k - lo
    return xs[lo] * (1 - frac) + xs[hi] * frac


def bench_direct(n: int = 100, history_length: int = 21):
    """Call compute_hmm_regime directly. Unique inputs each call (worst case: no cache hits)."""
    _clear_hmm_cache()
    histories = []
    for i in range(n):
        # Vary histories to defeat caching — worst-case scenario
        hist = [30.0 + (j + i) * 0.5 for j in range(history_length)]
        histories.append(hist)

    samples_us = []
    for i, hist in enumerate(histories):
        t0 = time.perf_counter()
        result = compute_hmm_regime(hist, 30.0 + i * 0.1)
        t1 = time.perf_counter()
        assert result is not None
        samples_us.append((t1 - t0) * 1e6)
    return samples_us


def bench_direct_cached(n: int = 100, history_length: int = 21):
    """Call compute_hmm_regime with a small set of repeated inputs (realistic cache hit)."""
    _clear_hmm_cache()
    # 5 unique histories repeated 20 times = 95% cache hits
    unique_histories = [
        [30.0 + (j + i) * 0.5 for j in range(history_length)] for i in range(5)
    ]
    sequence = []
    for _ in range(n // len(unique_histories) + 1):
        for h in unique_histories:
            sequence.append(h)
    sequence = sequence[:n]

    samples_us = []
    for hist in sequence:
        t0 = time.perf_counter()
        result = compute_hmm_regime(hist, 30.0)
        t1 = time.perf_counter()
        assert result is not None
        samples_us.append((t1 - t0) * 1e6)
    return samples_us


def bench_preflight(n: int = 100):
    """End-to-end preflight benchmark via TestClient."""
    try:
        from fastapi.testclient import TestClient
        from api.main import app, API_KEYS
    except Exception as exc:
        print(f"[skip] Could not import api.main for preflight bench: {exc}")
        return None

    # Ensure a demo key exists
    key = "sg_live_bench_hmm_opt_key"
    API_KEYS[key] = {"tier": "growth", "calls_this_month": 0, "customer_id": None, "email": "bench@local"}
    client = TestClient(app)

    entry = {
        "id": "m1",
        "content": "Bench entry",
        "type": "semantic",
        "timestamp_age_days": 1.0,
        "source_trust": 0.8,
        "source_conflict": 0.1,
        "downstream_count": 2,
    }

    # Use 21-length history (minimum that triggers HMM)
    base_hist = [30.0 + i * 0.5 for i in range(21)]

    headers = {"Authorization": f"Bearer {key}"}

    # Warmup
    for _ in range(3):
        client.post(
            "/v1/preflight",
            json={"memory_state": [entry], "score_history": base_hist},
            headers=headers,
        )

    samples_ms = []
    for i in range(n):
        # Vary history slightly so each call is unique (worst-case for cache)
        hist = [30.0 + (j + i) * 0.1 for j in range(21)]
        t0 = time.perf_counter()
        resp = client.post(
            "/v1/preflight",
            json={"memory_state": [entry], "score_history": hist},
            headers=headers,
        )
        t1 = time.perf_counter()
        assert resp.status_code == 200, resp.text
        samples_ms.append((t1 - t0) * 1e3)
    return samples_ms


def main():
    baseline = {}
    if BASELINE_PATH.exists():
        with open(BASELINE_PATH) as f:
            profile = json.load(f)
        baseline["hmm_ms"] = profile["all_modules_sorted"][0]["mean_us"] / 1000.0
        baseline["e2e_ms"] = profile["end_to_end_preflight_ms"]

    print("=" * 70)
    print("HMM OPTIMIZATION BENCHMARK")
    print("=" * 70)

    print("\n[1] Direct HMM calls (unique inputs, no cache hits) — n=100")
    direct = bench_direct(n=100, history_length=21)
    print(f"    mean: {statistics.mean(direct):>9.1f} us")
    print(f"    p50:  {percentile(direct, 50):>9.1f} us")
    print(f"    p99:  {percentile(direct, 99):>9.1f} us")
    if "hmm_ms" in baseline:
        speedup = (baseline["hmm_ms"] * 1000) / statistics.mean(direct)
        print(f"    baseline (module_latency_profile.json): {baseline['hmm_ms']*1000:.1f} us")
        print(f"    speedup: {speedup:.1f}x")

    print("\n[2] Direct HMM calls (5 unique inputs repeated, ~95% cache hits) — n=100")
    cached = bench_direct_cached(n=100, history_length=21)
    print(f"    mean: {statistics.mean(cached):>9.1f} us")
    print(f"    p50:  {percentile(cached, 50):>9.1f} us")
    print(f"    p99:  {percentile(cached, 99):>9.1f} us")
    if cached:
        print(f"    first-call (cold): {cached[0]:.1f} us, second (warm): {cached[5]:.1f} us")

    print("\n[3] End-to-end /v1/preflight with 21-length history — n=100")
    e2e = bench_preflight(n=100)
    if e2e is not None:
        print(f"    mean: {statistics.mean(e2e):>7.2f} ms")
        print(f"    p50:  {percentile(e2e, 50):>7.2f} ms")
        print(f"    p99:  {percentile(e2e, 99):>7.2f} ms")
        if "e2e_ms" in baseline:
            # Baseline 17.68 ms was measured WITHOUT HMM in the preflight path
            # (it profiles the HMM module separately). Our post-opt end-to-end
            # includes HMM, so a meaningful compare is: target < baseline + (post-opt HMM).
            post_hmm_ms = statistics.mean(direct) / 1000.0
            target_pct = (post_hmm_ms / statistics.mean(e2e)) * 100
            print(f"    baseline end-to-end (pre-HMM-addition): {baseline['e2e_ms']:.2f} ms")
            print(f"    HMM share of current e2e: ~{target_pct:.1f}% (target: <30%)")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    if "hmm_ms" in baseline:
        print(f"HMM direct-call baseline: {baseline['hmm_ms']*1000:.0f} us  (55.59 ms reported)")
        print(f"HMM direct-call post-opt: {statistics.mean(direct):.0f} us  "
              f"({((baseline['hmm_ms']*1000) / statistics.mean(direct)):.1f}x faster)")
        print(f"HMM with cache hit:       {statistics.mean(cached):.0f} us  "
              f"({((baseline['hmm_ms']*1000) / max(statistics.mean(cached), 1e-6)):.0f}x faster)")


if __name__ == "__main__":
    main()
