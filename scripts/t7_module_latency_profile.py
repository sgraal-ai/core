"""
T7 — Per-Module Latency Profile

Times N=100 direct invocations of each major scoring-engine analytics module
with representative inputs, plus one end-to-end /v1/preflight baseline.
Writes /Users/zsobrakpeter/core/research/results/module_latency_profile.json.
"""

from __future__ import annotations

import json
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore")

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402

# Direct module imports --------------------------------------------------------
from scoring_engine.omega_mem import compute as compute_omega, MemoryEntry
from scoring_engine.lyapunov import compute_lyapunov
from scoring_engine.lyapunov_exponent import compute_lyapunov_exponent
from scoring_engine.banach import compute_banach
from scoring_engine.hmm import compute_hmm_regime as compute_hmm
from scoring_engine.mdp import compute_mdp
from scoring_engine.mttr import compute_mttr
from scoring_engine.sheaf_cohomology import compute_sheaf_consistency
from scoring_engine.sinkhorn import sinkhorn_distance as compute_sinkhorn_wasserstein
from scoring_engine.rmt import compute_rmt
from scoring_engine.particle_filter import compute_particle_filter
from scoring_engine.hotelling_t2 import compute_hotelling_t2
from scoring_engine.kalman_forecast import KalmanForecaster
from scoring_engine.mahalanobis import compute_mahalanobis
from scoring_engine.copula import compute_copula
from scoring_engine.bocpd import compute_bocpd
from scoring_engine.free_energy import compute_free_energy
from scoring_engine.frechet import compute_frechet as compute_frechet_distance
from scoring_engine.pagerank import compute_pagerank
from scoring_engine.drift_detector import compute_drift_metrics as compute_drift

# Representative inputs --------------------------------------------------------
N = 100

SCORE_HISTORY_SHORT = [50.0 + (i % 7) * 2.0 for i in range(20)]
SCORE_HISTORY_LONG = [45.0 + (i % 11) * 3.0 for i in range(60)]

ENTRIES = [
    {
        "id": f"e{i}",
        "content": f"representative content token-{i} alpha beta gamma delta",
        "type": "semantic" if i % 2 else "episodic",
        "timestamp_age_days": 1.0 + i,
        "source_trust": 0.8,
        "source_conflict": 0.1,
        "downstream_count": i + 1,
    }
    for i in range(6)
]

MEMORY_ENTRIES = [
    MemoryEntry(
        id=f"m{i}",
        content=f"content {i} foo bar baz",
        type="semantic" if i % 2 else "episodic",
        timestamp_age_days=1.0 + i,
        source_trust=0.8,
        source_conflict=0.1,
        downstream_count=i + 1,
    )
    for i in range(5)
]

COMPONENT_BREAKDOWN = {
    "s_freshness": 40.0,
    "s_drift": 25.0,
    "s_provenance": 15.0,
    "s_relevance": 10.0,
    "r_belief": 0.5,
}

ADJACENCY = {
    "e0": ["e1", "e2"],
    "e1": ["e2"],
    "e2": ["e3"],
    "e3": [],
    "e4": ["e1", "e3"],
    "e5": ["e0"],
}


def _bench(label: str, fn, *args, **kwargs) -> dict:
    """Run fn N times, return mean/median/min latency in microseconds."""
    # one warm-up call — surface signature errors early
    try:
        fn(*args, **kwargs)
    except Exception as e:  # noqa: BLE001
        return {"module": label, "mean_us": None, "median_us": None,
                "min_us": None, "error": f"{type(e).__name__}: {str(e)[:120]}"}

    samples: list[float] = []
    t_start = time.perf_counter()
    for _ in range(N):
        t0 = time.perf_counter()
        try:
            fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            return {"module": label, "mean_us": None, "median_us": None,
                    "min_us": None, "error": f"{type(e).__name__}: {str(e)[:120]}"}
        samples.append((time.perf_counter() - t0) * 1_000_000.0)
    t_total = time.perf_counter() - t_start

    samples.sort()
    mean_us = sum(samples) / len(samples)
    median_us = samples[len(samples) // 2]
    min_us = samples[0]
    return {
        "module": label,
        "mean_us": round(mean_us, 3),
        "median_us": round(median_us, 3),
        "min_us": round(min_us, 3),
        "total_wall_ms": round(t_total * 1000.0, 3),
    }


def _kalman_cycle(history: list[float]) -> None:
    kf = KalmanForecaster()
    kf.fit(history)
    kf.predict(5)


def main() -> None:
    results: list[dict] = []

    # omega_mem full compute (uses the whole engine) — reference upper bound
    results.append(_bench(
        "omega_mem.compute",
        compute_omega, MEMORY_ENTRIES, "reversible", "general",
    ))

    results.append(_bench(
        "lyapunov.compute_lyapunov",
        compute_lyapunov, 3, 5.0, "REFETCH", 60.0,
    ))
    results.append(_bench(
        "lyapunov_exponent.compute_lyapunov_exponent",
        compute_lyapunov_exponent, SCORE_HISTORY_SHORT, 52.0,
    ))
    results.append(_bench(
        "banach.compute_banach",
        compute_banach, SCORE_HISTORY_SHORT, 52.0,
    ))
    results.append(_bench(
        "hmm.compute_hmm_regime",
        compute_hmm, SCORE_HISTORY_LONG, 50.0,
    ))
    results.append(_bench(
        "mdp.compute_mdp",
        compute_mdp, 55.0, None,
    ))
    results.append(_bench(
        "mttr.compute_mttr",
        compute_mttr, [5.0, 8.0, 12.0, 6.0, 9.0, 14.0, 7.0, 11.0],
    ))
    results.append(_bench(
        "sheaf_cohomology.compute_sheaf_consistency",
        compute_sheaf_consistency, ENTRIES,
    ))
    results.append(_bench(
        "sinkhorn.sinkhorn_distance",
        compute_sinkhorn_wasserstein,
        [0.1, 0.2, 0.3, 0.2, 0.2],
        [0.15, 0.25, 0.2, 0.2, 0.2],
    ))
    results.append(_bench(
        "rmt.compute_rmt",
        compute_rmt, ENTRIES,
    ))
    results.append(_bench(
        "particle_filter.compute_particle_filter",
        compute_particle_filter, 52.0, None, None, 50, "bench",
    ))
    results.append(_bench(
        "hotelling_t2.compute_hotelling_t2",
        compute_hotelling_t2, COMPONENT_BREAKDOWN, None,
    ))
    results.append(_bench(
        "kalman_forecast.KalmanForecaster.fit+predict",
        _kalman_cycle, SCORE_HISTORY_SHORT,
    ))
    results.append(_bench(
        "mahalanobis.compute_mahalanobis",
        compute_mahalanobis, ENTRIES,
    ))
    results.append(_bench(
        "copula.compute_copula",
        compute_copula, 0.4, 0.3, 0.7,
    ))
    results.append(_bench(
        "bocpd.compute_bocpd",
        compute_bocpd, SCORE_HISTORY_LONG,
    ))
    results.append(_bench(
        "free_energy.compute_free_energy",
        compute_free_energy, 52.0, 0.55, COMPONENT_BREAKDOWN, None,
    ))
    results.append(_bench(
        "frechet.compute_frechet",
        compute_frechet_distance,
        [[0.1, 0.2, 0.3], [0.2, 0.3, 0.4], [0.15, 0.25, 0.35],
         [0.12, 0.22, 0.32], [0.18, 0.28, 0.38]],
        [[0.1, 0.2, 0.3], [0.2, 0.3, 0.4], [0.15, 0.25, 0.35],
         [0.12, 0.22, 0.32], [0.18, 0.28, 0.38]],
        5,
    ))
    results.append(_bench(
        "pagerank.compute_pagerank",
        compute_pagerank, ADJACENCY,
    ))
    results.append(_bench(
        "drift_detector.compute_drift_metrics",
        compute_drift,
        [0.1, 0.2, 0.3, 0.2, 0.2, 0.15, 0.25, 0.18],
        [0.12, 0.18, 0.32, 0.22, 0.16, 0.14, 0.26, 0.22],
    ))

    # end-to-end preflight baseline --------------------------------------------
    client = TestClient(app)
    AUTH = {"Authorization": "Bearer sg_test_key_001"}
    body = {
        "memory_state": [
            {
                "id": f"e{i}",
                "content": f"bench content {i}",
                "type": "semantic" if i % 2 else "episodic",
                "timestamp_age_days": 1.0 + i,
                "source_trust": 0.8,
                "source_conflict": 0.1,
                "downstream_count": i + 1,
            }
            for i in range(5)
        ],
        "action_type": "reversible",
        "domain": "general",
    }
    # warm-up
    client.post("/v1/preflight", json=body, headers=AUTH)

    t0 = time.perf_counter()
    for _ in range(N):
        client.post("/v1/preflight", json=body, headers=AUTH)
    end_to_end_ms = (time.perf_counter() - t0) / N * 1000.0

    # summarise -----------------------------------------------------------------
    valid = [r for r in results if r.get("mean_us") is not None]
    valid.sort(key=lambda r: r["mean_us"], reverse=True)
    total_us = sum(r["mean_us"] for r in valid) or 1.0
    for r in valid:
        r["pct_of_profiled_total"] = round(100.0 * r["mean_us"] / total_us, 2)

    errored = [r for r in results if r.get("mean_us") is None]

    top10 = [
        {"module": r["module"], "mean_us": r["mean_us"],
         "pct_of_profiled_total": r["pct_of_profiled_total"]}
        for r in valid[:10]
    ]

    # Interpretation
    profiled_sum_ms = total_us / 1000.0
    ratio = profiled_sum_ms / end_to_end_ms if end_to_end_ms else 0.0
    heaviest = valid[0]["module"] if valid else "n/a"
    top3_share = sum(r["pct_of_profiled_total"] for r in valid[:3])

    interpretation = (
        f"End-to-end preflight: {end_to_end_ms:.2f} ms. "
        f"Sum of profiled module means: {profiled_sum_ms:.2f} ms "
        f"({ratio * 100:.1f}% of E2E budget). "
        f"Heaviest module: {heaviest}. "
        f"Top-3 modules account for {top3_share:.1f}% of profiled time."
    )

    optimization_targets = [r["module"] for r in valid[:5]]

    out = {
        "n_samples": N,
        "end_to_end_preflight_ms": round(end_to_end_ms, 3),
        "modules_profiled": len(valid),
        "modules_errored": len(errored),
        "sum_profiled_ms": round(profiled_sum_ms, 3),
        "profiled_vs_e2e_ratio": round(ratio, 3),
        "top_10_slowest": top10,
        "all_modules_sorted": valid,
        "errored_modules": errored,
        "interpretation": interpretation,
        "optimization_targets": optimization_targets,
    }

    out_path = "/Users/zsobrakpeter/core/research/results/module_latency_profile.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    print(f"[t7] profiled {len(valid)} modules, {len(errored)} errored")
    print(f"[t7] E2E preflight: {end_to_end_ms:.2f} ms")
    print(f"[t7] top-5 heaviest: {[m['module'] for m in top10[:5]]}")
    print(f"[t7] wrote {out_path}")


if __name__ == "__main__":
    main()
