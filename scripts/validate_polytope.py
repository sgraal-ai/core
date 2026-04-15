#!/usr/bin/env python3
"""
Validate the Risk Polytope. Three tasks:
1. Domain-specific PCA — is d=5 universal?
2. Leave-one-out κ_MEM stability — robust invariant?
3. Decision region mapping — are boundaries linear?
"""
import sys, os, math, json, random, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"

from fastapi.testclient import TestClient
from api.main import app, _load_benchmark_corpus

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

COMPONENT_KEYS = ["s_freshness", "s_drift", "s_provenance", "s_propagation",
                  "r_recall", "r_encode", "s_interference", "s_recovery",
                  "r_belief", "s_relevance", "omega", "assurance"]


def run_preflight(case):
    r = client.post("/v1/preflight", headers=AUTH, json={
        "memory_state": case["memory_state"],
        "action_type": case.get("action_type", "reversible"),
        "domain": case.get("domain", "general"),
        "dry_run": True,
    })
    if r.status_code != 200:
        return None
    return r.json()


def extract_vector(pf):
    cb = pf.get("component_breakdown", {})
    vec = [cb.get(k, 0) / 100.0 for k in COMPONENT_KEYS[:10]]
    vec.append(pf.get("omega_mem_final", 0) / 100.0)
    vec.append(pf.get("assurance_score", 0) / 100.0)
    return vec


# =========================================================================
# TASK 1: Domain-specific PCA
# =========================================================================

def task1_domain_pca():
    print("=" * 60)
    print("  TASK 1: DOMAIN-SPECIFIC PCA")
    print("=" * 60)

    cases = _load_benchmark_corpus()
    print(f"\n  Loaded {len(cases)} corpus cases")

    # Run all through preflight and collect vectors by domain
    domain_vectors: dict[str, list] = {}
    domain_decisions: dict[str, list] = {}

    for i, case in enumerate(cases):
        pf = run_preflight(case)
        if not pf:
            continue
        dom = case.get("domain", "general")
        vec = extract_vector(pf)
        if dom not in domain_vectors:
            domain_vectors[dom] = []
            domain_decisions[dom] = []
        domain_vectors[dom].append(vec)
        domain_decisions[dom].append(pf.get("recommended_action", "USE_MEMORY"))
        if (i + 1) % 100 == 0:
            print(f"    {i+1}/{len(cases)}...")

    # Also collect ALL vectors for comparison
    all_vectors = []
    all_decisions = []
    for dom in domain_vectors:
        all_vectors.extend(domain_vectors[dom])
        all_decisions.extend(domain_decisions[dom])

    results = {}

    for dom, vecs in sorted(domain_vectors.items()):
        X = np.array(vecs)
        n, d = X.shape
        if n < 5:
            results[dom] = {"n_samples": n, "skipped": "too_few_samples"}
            continue

        # Remove zero-variance
        var = np.var(X, axis=0)
        active = var > 1e-8
        Xa = X[:, active]
        active_names = [COMPONENT_KEYS[i] for i in range(d) if active[i]]

        if Xa.shape[1] < 2:
            results[dom] = {"n_samples": n, "skipped": "too_few_active_dims"}
            continue

        # PCA
        cov = np.cov(Xa, rowvar=False)
        cov = np.nan_to_num(cov)
        eig_vals, eig_vecs = np.linalg.eigh(cov)
        idx = np.argsort(eig_vals)[::-1]
        eig_vals = eig_vals[idx]
        eig_vecs = eig_vecs[:, idx]

        # Marchenko-Pastur
        gamma = n / Xa.shape[1]
        mp_upper = (1 + 1/np.sqrt(gamma))**2 if gamma > 0 else 999
        # Use correlation matrix eigenvalues for MP comparison
        corr = np.corrcoef(Xa, rowvar=False)
        corr = np.nan_to_num(corr)
        corr_eigs = np.sort(np.linalg.eigvalsh(corr))[::-1]
        signal_count = int(np.sum(corr_eigs > mp_upper))

        # 95% variance
        total_var = np.sum(eig_vals)
        if total_var > 0:
            cumvar = np.cumsum(eig_vals) / total_var
            k_95 = int(np.searchsorted(cumvar, 0.95)) + 1
        else:
            k_95 = Xa.shape[1]

        # PC1 top loadings
        pc1 = eig_vecs[:, 0]
        top3_idx = np.argsort(np.abs(pc1))[::-1][:3]
        pc1_loadings = [(active_names[j], round(float(pc1[j]), 3)) for j in top3_idx]

        results[dom] = {
            "n_samples": n,
            "active_dimensions": int(Xa.shape[1]),
            "intrinsic_dimension_mp": signal_count,
            "dimensions_95pct_variance": k_95,
            "top_eigenvalues": [round(float(e), 4) for e in corr_eigs[:8]],
            "pc1_top_loadings": pc1_loadings,
        }

        print(f"\n  {dom}: n={n}, d_MP={signal_count}, d_95={k_95}, PC1={pc1_loadings}")

    # Summary
    dims_mp = [r.get("intrinsic_dimension_mp", 0) for r in results.values() if isinstance(r.get("intrinsic_dimension_mp"), int)]
    dims_95 = [r.get("dimensions_95pct_variance", 0) for r in results.values() if isinstance(r.get("dimensions_95pct_variance"), int)]

    print(f"\n  SUMMARY:")
    print(f"  Intrinsic dimensions (MP): {dims_mp}")
    print(f"  Dimensions for 95% var:    {dims_95}")
    if dims_mp:
        print(f"  Mean d_MP: {np.mean(dims_mp):.1f}, Std: {np.std(dims_mp):.1f}")
    if len(set(dims_mp)) == 1:
        print(f"  → d={dims_mp[0]} IS UNIVERSAL across domains")
    else:
        print(f"  → d is DOMAIN-DEPENDENT (varies {min(dims_mp)}-{max(dims_mp)})")

    return results, all_vectors, all_decisions


# =========================================================================
# TASK 2: Leave-one-out κ_MEM stability
# =========================================================================

def task2_kappa_loo(all_vectors):
    print("\n" + "=" * 60)
    print("  TASK 2: LEAVE-ONE-OUT κ_MEM STABILITY")
    print("=" * 60)

    X = np.array(all_vectors)
    n, d = X.shape
    var = np.var(X, axis=0)
    active = var > 1e-8
    active_names = [COMPONENT_KEYS[i] for i in range(d) if active[i]]

    # Baseline κ_MEM (all signals)
    def compute_kappa(data):
        corr = np.corrcoef(data, rowvar=False)
        corr = np.nan_to_num(corr)
        abs_c = np.abs(corr)
        np.fill_diagonal(abs_c, 0)
        thresholds = np.linspace(0.0, 0.10, 501)
        for t in thresholds:
            adj = (abs_c > t).astype(float)
            deg = np.sum(adj, axis=1)
            L = np.diag(deg) - adj
            eigs = np.linalg.eigvalsh(L)
            eigs.sort()
            if len(eigs) > 1 and eigs[1] < 1e-6:
                return float(t)
        return 0.10

    X_active = X[:, active]
    baseline = compute_kappa(X_active)
    print(f"\n  Baseline κ_MEM (all signals): {baseline:.4f}")

    loo_results = []
    for i in range(len(active_names)):
        # Drop signal i
        mask = list(range(X_active.shape[1]))
        mask.pop(i)
        X_dropped = X_active[:, mask]
        kappa = compute_kappa(X_dropped)
        shift = kappa - baseline
        loo_results.append({
            "dropped_signal": active_names[i],
            "kappa": round(kappa, 4),
            "shift": round(shift, 4),
        })
        print(f"    Drop {active_names[i]:15s}: κ={kappa:.4f} (Δ={shift:+.4f})")

    kappas = [r["kappa"] for r in loo_results]
    shifts = [abs(r["shift"]) for r in loo_results]
    most_influential = loo_results[np.argmax(shifts)]

    print(f"\n  Mean κ: {np.mean(kappas):.4f}")
    print(f"  Std κ:  {np.std(kappas):.4f}")
    print(f"  Range:  [{min(kappas):.4f}, {max(kappas):.4f}]")
    print(f"  Most influential: {most_influential['dropped_signal']} (shift={most_influential['shift']:+.4f})")

    if np.std(kappas) < 0.005:
        print(f"  → κ_MEM IS ROBUST (std < 0.005)")
        robust = True
    else:
        print(f"  → κ_MEM IS SENSITIVE to signal composition (std >= 0.005)")
        robust = False

    return {
        "baseline_kappa": round(baseline, 4),
        "leave_one_out": loo_results,
        "mean_kappa": round(float(np.mean(kappas)), 4),
        "std_kappa": round(float(np.std(kappas)), 4),
        "min_kappa": round(float(min(kappas)), 4),
        "max_kappa": round(float(max(kappas)), 4),
        "most_influential_signal": most_influential["dropped_signal"],
        "most_influential_shift": most_influential["shift"],
        "robust": robust,
    }


# =========================================================================
# TASK 3: Decision region mapping
# =========================================================================

def task3_decision_regions(all_vectors, all_decisions):
    print("\n" + "=" * 60)
    print("  TASK 3: DECISION REGION MAPPING")
    print("=" * 60)

    X = np.array(all_vectors)
    var = np.var(X, axis=0)
    active = var > 1e-8
    X_active = X[:, active]

    # PCA on all data
    cov = np.cov(X_active, rowvar=False)
    cov = np.nan_to_num(cov)
    eig_vals, eig_vecs = np.linalg.eigh(cov)
    idx = np.argsort(eig_vals)[::-1]
    eig_vals = eig_vals[idx]
    eig_vecs = eig_vecs[:, idx]

    # Project onto top 5 PCs
    X_proj = X_active @ eig_vecs[:, :5]

    # Label decisions
    decisions = np.array(all_decisions)
    is_use = decisions == "USE_MEMORY"
    is_warn = np.isin(decisions, ["WARN", "ASK_USER"])
    is_block = decisions == "BLOCK"

    n_use = np.sum(is_use)
    n_warn = np.sum(is_warn)
    n_block = np.sum(is_block)
    print(f"\n  Decisions: USE_MEMORY={n_use}, WARN/ASK={n_warn}, BLOCK={n_block}")

    # PC1 distribution per decision
    pc1_use = X_proj[is_use, 0] if n_use > 0 else np.array([])
    pc1_warn = X_proj[is_warn, 0] if n_warn > 0 else np.array([])
    pc1_block = X_proj[is_block, 0] if n_block > 0 else np.array([])

    print(f"\n  PC1 distribution:")
    if len(pc1_use) > 0:
        print(f"    USE_MEMORY: mean={np.mean(pc1_use):.4f}, std={np.std(pc1_use):.4f}, range=[{np.min(pc1_use):.4f}, {np.max(pc1_use):.4f}]")
    if len(pc1_warn) > 0:
        print(f"    WARN/ASK:   mean={np.mean(pc1_warn):.4f}, std={np.std(pc1_warn):.4f}, range=[{np.min(pc1_warn):.4f}, {np.max(pc1_warn):.4f}]")
    if len(pc1_block) > 0:
        print(f"    BLOCK:      mean={np.mean(pc1_block):.4f}, std={np.std(pc1_block):.4f}, range=[{np.min(pc1_block):.4f}, {np.max(pc1_block):.4f}]")

    # Find optimal threshold on PC1 to separate USE from WARN+BLOCK
    best_thresh_uw = 0.0
    best_acc_uw = 0.0
    y_uw = np.where(is_use, 0, 1)  # 0=USE, 1=WARN+BLOCK
    for t in np.linspace(np.min(X_proj[:, 0]), np.max(X_proj[:, 0]), 200):
        pred = (X_proj[:, 0] < t).astype(int)  # PC1 is negatively correlated with omega
        acc = np.mean(pred == y_uw)
        if acc > best_acc_uw:
            best_acc_uw = acc
            best_thresh_uw = t

    # Find threshold to separate WARN from BLOCK
    warn_block_mask = is_warn | is_block
    if np.sum(warn_block_mask) > 5:
        X_wb = X_proj[warn_block_mask, 0]
        y_wb = np.where(is_block[warn_block_mask], 1, 0)
        best_thresh_wb = 0.0
        best_acc_wb = 0.0
        for t in np.linspace(np.min(X_wb), np.max(X_wb), 200):
            pred = (X_wb < t).astype(int)
            acc = np.mean(pred == y_wb)
            if acc > best_acc_wb:
                best_acc_wb = acc
                best_thresh_wb = t
    else:
        best_thresh_wb = 0.0
        best_acc_wb = 0.0

    # Multi-class accuracy using PC1 alone (2 thresholds)
    if n_use > 0 and n_block > 0:
        # Predict: PC1 > thresh_uw → USE, PC1 < thresh_wb → BLOCK, else WARN
        # PC1 is inversely related to risk (negative loading on omega)
        pred_multi = []
        for p in X_proj[:, 0]:
            if p > best_thresh_uw:
                pred_multi.append("USE_MEMORY")
            elif p < best_thresh_wb:
                pred_multi.append("BLOCK")
            else:
                pred_multi.append("WARN")
        multi_acc = np.mean([p == d or (p == "WARN" and d in ("WARN", "ASK_USER"))
                            for p, d in zip(pred_multi, all_decisions)])
    else:
        multi_acc = 0.0

    # Is separation linear? Check using first 2 PCs
    # If PC1 alone gives >80% accuracy, separation is essentially linear
    linear_separation = best_acc_uw > 0.8

    print(f"\n  SEPARATION ANALYSIS:")
    print(f"  USE vs WARN+BLOCK threshold on PC1: {best_thresh_uw:.4f} (accuracy: {best_acc_uw*100:.1f}%)")
    print(f"  WARN vs BLOCK threshold on PC1:     {best_thresh_wb:.4f} (accuracy: {best_acc_wb*100:.1f}%)")
    print(f"  3-class accuracy (PC1 alone):        {multi_acc*100:.1f}%")
    print(f"  Linear separation: {'YES' if linear_separation else 'NO'} ({best_acc_uw*100:.1f}% on PC1)")

    return {
        "n_samples": len(all_decisions),
        "decision_counts": {"USE_MEMORY": int(n_use), "WARN_ASK": int(n_warn), "BLOCK": int(n_block)},
        "pc1_stats": {
            "use_memory_mean": round(float(np.mean(pc1_use)), 4) if len(pc1_use) > 0 else None,
            "warn_mean": round(float(np.mean(pc1_warn)), 4) if len(pc1_warn) > 0 else None,
            "block_mean": round(float(np.mean(pc1_block)), 4) if len(pc1_block) > 0 else None,
        },
        "use_vs_warnblock_threshold": round(float(best_thresh_uw), 4),
        "use_vs_warnblock_accuracy": round(float(best_acc_uw), 4),
        "warn_vs_block_threshold": round(float(best_thresh_wb), 4),
        "warn_vs_block_accuracy": round(float(best_acc_wb), 4),
        "multiclass_accuracy_pc1_only": round(float(multi_acc), 4),
        "linear_separation": bool(linear_separation),
    }


# =========================================================================
# MAIN
# =========================================================================

if __name__ == "__main__":
    t0 = time.time()

    r1, all_vecs, all_decs = task1_domain_pca()
    r2 = task2_kappa_loo(all_vecs)
    r3 = task3_decision_regions(all_vecs, all_decs)

    combined = {
        "task1_domain_pca": r1,
        "task2_kappa_loo": r2,
        "task3_decision_regions": r3,
        "elapsed_seconds": round(time.time() - t0, 1),
    }

    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "research", "results", "polytope_validation.json")
    with open(out_path, "w") as f:
        json.dump(combined, f, indent=2, default=lambda x: int(x) if isinstance(x, (np.integer, np.bool_)) else float(x) if isinstance(x, np.floating) else x)

    print("\n" + "=" * 60)
    print("  ALL TASKS COMPLETE")
    print("=" * 60)
    print(f"  Time: {time.time()-t0:.1f}s")
    print(f"  Saved to {out_path}")
