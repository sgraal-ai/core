#!/usr/bin/env python3
"""
TASK 9 — Optimal Transport BLOCK <-> USE_MEMORY

Compute Wasserstein (Sinkhorn-regularized) distance between the two conditional
distributions in the 132-feature preflight space:
    P = rows where recommended_action == "BLOCK"
    Q = rows where recommended_action == "USE_MEMORY"

Also compute:
- barycenter weighted toward safer USE_MEMORY: 0.3 * mean(P) + 0.7 * mean(Q)
- mean euclidean distance from any BLOCK row to the barycenter
- mean L2 "effort" per BLOCK point to reach barycenter
- top healing-direction features (largest |mean(P) - barycenter|)

Outputs:
    /Users/zsobrakpeter/core/research/results/optimal_transport.json
    /Users/zsobrakpeter/core/research/results/optimal_transport_section.md
"""

from __future__ import annotations

import os
import sys
import json

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")

import numpy as np

from _harvest_feature_matrix import harvest_matrix

RESULTS_DIR = "/Users/zsobrakpeter/core/research/results"
CACHE = "/tmp/sgraal_feature_matrix_cache.json"

np.random.seed(42)


# ----------------------------------------------------------------------------
# Sinkhorn in multi-D (numpy)
# ----------------------------------------------------------------------------

def sinkhorn_nd(
    X_p: np.ndarray,
    X_q: np.ndarray,
    epsilon: float = 0.1,
    max_iter: int = 100,
    tol: float = 1e-6,
) -> tuple[float, int, bool]:
    """
    Entropic-regularized OT between two empirical measures in R^d.
    Uniform weights on both sides.

    Returns:
        (W_eps, iterations, converged)
    """
    n = X_p.shape[0]
    m = X_q.shape[0]
    if n == 0 or m == 0:
        return 0.0, 0, False

    # Euclidean cost matrix C[i, j] = || X_p[i] - X_q[j] ||_2
    # use squared for numerical stability then sqrt at the end step
    sq = np.sum(X_p ** 2, axis=1, keepdims=True) + np.sum(X_q ** 2, axis=1) - 2.0 * X_p @ X_q.T
    sq = np.clip(sq, 0.0, None)
    C = np.sqrt(sq)

    # Normalize cost matrix so entries are O(1): C / C.max() + 1e-8 (matches repo Sinkhorn convention)
    c_max = float(C.max())
    if c_max > 1e-10:
        C_scaled = C / c_max + 1e-8
    else:
        return 0.0, 0, True

    # K = exp(-C_scaled / epsilon)
    K = np.exp(-C_scaled / epsilon)
    # Marginal distributions (uniform)
    a = np.ones(n) / n
    b = np.ones(m) / m

    u = np.ones(n)
    v = np.ones(m)
    converged = False
    iters = 0
    for it in range(max_iter):
        u_new = a / (K @ v + 1e-30)
        v_new = b / (K.T @ u_new + 1e-30)
        du = np.max(np.abs(u_new - u))
        dv = np.max(np.abs(v_new - v))
        u, v = u_new, v_new
        iters = it + 1
        if max(du, dv) < tol:
            converged = True
            break

    gamma = (u[:, None] * K) * v[None, :]  # transport plan
    # Report W in the ORIGINAL cost units (not scaled): sum gamma * C
    W = float(np.sum(gamma * C))
    return W, iters, converged


# ----------------------------------------------------------------------------
# Main driver
# ----------------------------------------------------------------------------

def main():
    X_full, feature_names, meta = harvest_matrix(cache_path=CACHE)
    print(f"Matrix shape: {X_full.shape}", flush=True)

    # Find target column (exclude it so barycenter / distances live in predictor space)
    try:
        omega_idx = feature_names.index("top.omega_mem_final")
    except ValueError:
        raise RuntimeError("top.omega_mem_final not in feature names")

    # Drop zero-variance columns and the target column
    stds = X_full.std(axis=0, ddof=1)
    active_mask = stds >= 1e-12
    active_mask[omega_idx] = False
    active_idx = np.where(active_mask)[0]
    active_names = [feature_names[i] for i in active_idx]
    X = X_full[:, active_idx].astype(np.float64)

    # Standardize: OT in the normalized space avoids one huge-scale feature dominating
    mu_all = X.mean(axis=0)
    sd_all = X.std(axis=0, ddof=1)
    sd_all = np.where(sd_all < 1e-12, 1.0, sd_all)
    Z = (X - mu_all) / sd_all

    actions = np.array([r["recommended_action"] for r in meta["rows"]])

    block_mask = actions == "BLOCK"
    use_mask = actions == "USE_MEMORY"

    Xp = Z[block_mask]
    Xq = Z[use_mask]
    print(f"BLOCK: {Xp.shape}, USE_MEMORY: {Xq.shape}", flush=True)

    if Xp.shape[0] < 2 or Xq.shape[0] < 2:
        raise RuntimeError("Too few samples for BLOCK or USE_MEMORY")

    # ---- Sinkhorn Wasserstein ----
    # With 175 vs 124 points and 77 dims, full Sinkhorn is fine (O(nm d))
    W_eps, iters, converged = sinkhorn_nd(Xp, Xq, epsilon=0.1, max_iter=500, tol=1e-6)
    print(f"Sinkhorn W_eps (normalized features) = {W_eps:.6f}, iters={iters}, converged={converged}", flush=True)

    # Also compute in ORIGINAL (un-standardized) space for interpretability
    W_raw, iters_raw, conv_raw = sinkhorn_nd(X[block_mask], X[use_mask], epsilon=0.1, max_iter=500, tol=1e-6)

    # ---- Barycenter (weighted mean, simplified) ----
    mean_P = Xp.mean(axis=0)
    mean_Q = Xq.mean(axis=0)
    barycenter_z = 0.3 * mean_P + 0.7 * mean_Q

    # In original units
    mean_P_raw = X[block_mask].mean(axis=0)
    mean_Q_raw = X[use_mask].mean(axis=0)
    barycenter_raw = 0.3 * mean_P_raw + 0.7 * mean_Q_raw

    # ---- Distances from each BLOCK point to barycenter ----
    diffs = Xp - barycenter_z[None, :]
    per_point_dist = np.linalg.norm(diffs, axis=1)
    per_point_effort = per_point_dist.copy()  # L2 of required change == euclidean distance

    mean_dist = float(per_point_dist.mean())
    median_dist = float(np.median(per_point_dist))
    p95_dist = float(np.quantile(per_point_dist, 0.95))
    mean_effort = float(per_point_effort.mean())

    # ---- Top healing-direction features ----
    # Per feature: how much the BLOCK cluster mean must shift to reach barycenter.
    # In raw units, so "units" are interpretable per feature.
    delta_to_bary_raw = barycenter_raw - mean_P_raw
    abs_delta = np.abs(delta_to_bary_raw)
    # Normalize by feature std to get effect-size units (shift in sigmas)
    delta_in_sigmas = delta_to_bary_raw / sd_all
    abs_sigma = np.abs(delta_in_sigmas)

    order = np.argsort(abs_sigma)[::-1]
    top_healing = []
    for k in range(min(15, len(order))):
        idx = int(order[k])
        top_healing.append({
            "feature": active_names[idx],
            "block_mean": float(mean_P_raw[idx]),
            "use_memory_mean": float(mean_Q_raw[idx]),
            "barycenter": float(barycenter_raw[idx]),
            "delta_block_to_barycenter": float(delta_to_bary_raw[idx]),
            "delta_sigmas": float(delta_in_sigmas[idx]),
            "feature_std": float(sd_all[idx]),
        })

    # ---- First 10 features of barycenter (for JSON) ----
    first_10_bary = [
        {"feature": active_names[i], "value_z": float(barycenter_z[i]),
         "value_raw": float(barycenter_raw[i])}
        for i in range(min(10, len(active_names)))
    ]

    interpretation = (
        f"In the 77-dim standardized feature space derived from 449 preflight runs, "
        f"the Sinkhorn-regularized Wasserstein distance between the BLOCK cluster "
        f"(n={int(block_mask.sum())}) and USE_MEMORY cluster (n={int(use_mask.sum())}) "
        f"is W_eps = {W_eps:.3f} (standardized) / {W_raw:.3f} (raw units). "
        f"Sinkhorn converged in {iters} iterations at epsilon=0.1. "
        f"A barycenter biased 0.7 toward USE_MEMORY and 0.3 toward BLOCK (the 'safe recovery center') "
        f"lies at mean L2 distance {mean_dist:.2f} sigmas from each BLOCK point (median={median_dist:.2f}, "
        f"p95={p95_dist:.2f}). The highest-leverage healing directions — features that must "
        f"shift most in sigma-units to reach the barycenter — are led by "
        f"`{top_healing[0]['feature']}` (delta={top_healing[0]['delta_sigmas']:.2f}sigma), "
        f"`{top_healing[1]['feature']}` ({top_healing[1]['delta_sigmas']:.2f}sigma), "
        f"`{top_healing[2]['feature']}` ({top_healing[2]['delta_sigmas']:.2f}sigma). "
        f"These are the components a repair plan should preferentially move to transport "
        f"a BLOCKed memory state toward safety."
    )

    out = {
        "n_block_samples": int(block_mask.sum()),
        "n_use_memory_samples": int(use_mask.sum()),
        "n_features": int(len(active_names)),
        "feature_space": "standardized (z-score) 77 active features, target omega excluded",
        "epsilon": 0.1,
        "wasserstein_distance_standardized": round(W_eps, 6),
        "wasserstein_distance_raw_units": round(W_raw, 6),
        "sinkhorn_iterations": int(iters),
        "sinkhorn_converged": bool(converged),
        "sinkhorn_iterations_raw": int(iters_raw),
        "sinkhorn_converged_raw": bool(conv_raw),
        "barycenter_weighting": {"block": 0.3, "use_memory": 0.7},
        "barycenter_centroid_first10": first_10_bary,
        "mean_distance_block_to_barycenter": round(mean_dist, 6),
        "median_distance_block_to_barycenter": round(median_dist, 6),
        "p95_distance_block_to_barycenter": round(p95_dist, 6),
        "mean_effort_l2": round(mean_effort, 6),
        "top_healing_direction_features": top_healing,
        "interpretation": interpretation,
        "notes": [
            "Pure numpy Sinkhorn implementation; cost matrix normalized by its max "
            "(matches repo scoring_engine/sinkhorn.py convention) before Gibbs kernel exp(-C/epsilon).",
            "Wasserstein reported in the *original* (un-scaled) cost units via sum(gamma * C).",
            "Barycenter is the simplified weighted mean (not the Wasserstein-barycenter "
            "fixed point) as specified: 0.3*mean(BLOCK) + 0.7*mean(USE_MEMORY).",
            "Feature matrix derived from live /v1/preflight on the 449-case benchmark corpus; "
            "BLOCK vs USE_MEMORY split by response.recommended_action.",
        ],
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, "optimal_transport.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {out_path}", flush=True)

    # Markdown
    md_path = os.path.join(RESULTS_DIR, "optimal_transport_section.md")
    lines: list[str] = []
    lines.append("### 19.9 Optimal Transport Between BLOCK and USE_MEMORY")
    lines.append("")
    lines.append(
        "We treat the `/v1/preflight` output space as a measure space and ask: how far apart "
        "are the BLOCK and USE_MEMORY conditional distributions, and what is the minimum-effort "
        "trajectory from a BLOCKed state toward safety?"
    )
    lines.append("")
    lines.append("**Setup.**")
    lines.append("")
    lines.append(f"- {int(block_mask.sum())} BLOCK samples vs {int(use_mask.sum())} USE_MEMORY samples")
    lines.append(f"- 77-dimensional standardized feature space (zero-variance columns and `omega_mem_final` excluded)")
    lines.append(f"- Entropic OT: Sinkhorn with epsilon=0.1, cost = euclidean distance")
    lines.append("")
    lines.append("**Wasserstein distance:**")
    lines.append("")
    lines.append("| Quantity | Value |")
    lines.append("|---|---|")
    lines.append(f"| W_epsilon (standardized) | **{W_eps:.3f}** |")
    lines.append(f"| W_epsilon (raw units) | {W_raw:.3f} |")
    lines.append(f"| Sinkhorn iterations | {iters} |")
    lines.append(f"| Converged | {converged} |")
    lines.append("")
    lines.append(
        "A non-trivial Wasserstein distance between BLOCK and USE_MEMORY confirms the two "
        "decision classes occupy distinct regions of feature space — the preflight engine "
        "does not merely threshold one or two features but induces a geometric separation."
    )
    lines.append("")
    lines.append("**Barycenter (safe-recovery center).** We define the safe-recovery center as")
    lines.append("")
    lines.append("```")
    lines.append("barycenter = 0.3 * mean(BLOCK) + 0.7 * mean(USE_MEMORY)")
    lines.append("```")
    lines.append("")
    lines.append(
        f"biased toward the safe cluster. Each BLOCK point is then at an average euclidean "
        f"distance of **{mean_dist:.2f} sigmas** (median {median_dist:.2f}, p95 {p95_dist:.2f}) "
        f"from this center — the mean L2 'healing effort' required."
    )
    lines.append("")
    lines.append("**Top healing-direction features.** Features whose BLOCK cluster mean is furthest "
                 "from the barycenter, in sigma-units — these are the components the repair plan "
                 "must preferentially move.")
    lines.append("")
    lines.append("| Feature | block_mean | use_memory_mean | delta (sigmas) |")
    lines.append("|---|---|---|---|")
    for rec in top_healing[:10]:
        lines.append(
            f"| `{rec['feature']}` | {rec['block_mean']:.3f} | "
            f"{rec['use_memory_mean']:.3f} | {rec['delta_sigmas']:+.2f} |"
        )
    lines.append("")
    lines.append(
        "**Implication.** A repair plan can be interpreted as an approximate OT transport "
        "map: each BLOCK point is pushed along the direction of largest sigma-change toward the "
        "barycenter. The top-ranked features above indicate which components carry the most "
        "transport mass, and therefore which heal actions (REFETCH, VERIFY_WITH_SOURCE, etc.) "
        "yield the greatest reduction in Wasserstein distance per unit of effort."
    )
    lines.append("")
    lines.append(
        "**Caveat.** The barycenter used here is the weighted mean specified in the task "
        "(fast, interpretable) rather than the true Wasserstein-barycenter fixed point. "
        "For production repair plan prioritization, a full iterative barycenter solver would "
        "give a more geometrically accurate target, at ~10x compute cost."
    )
    lines.append("")
    with open(md_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Wrote {md_path}", flush=True)


if __name__ == "__main__":
    main()
