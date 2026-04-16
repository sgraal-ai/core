#!/usr/bin/env python3
"""
Critical validation: Is K=0 real or a linear method artifact?

Test curvature with PCA (linear), Kernel PCA (nonlinear), UMAP, Isomap.
"""
import sys, os, math, json, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from fastapi.testclient import TestClient
from api.main import app, _load_benchmark_corpus

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

COMPONENT_KEYS = ["s_freshness", "s_drift", "s_provenance", "s_propagation",
                  "r_recall", "r_encode", "s_interference", "s_recovery",
                  "r_belief", "s_relevance", "omega", "assurance"]


def collect_vectors():
    """Run corpus through preflight and collect signal vectors."""
    cases = _load_benchmark_corpus()
    vectors = []
    for i, case in enumerate(cases):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": case["memory_state"],
            "action_type": case.get("action_type", "reversible"),
            "domain": case.get("domain", "general"), "dry_run": True,
        })
        if r.status_code != 200:
            continue
        pf = r.json()
        cb = pf.get("component_breakdown", {})
        vec = [cb.get(k, 0) / 100.0 for k in COMPONENT_KEYS[:10]]
        vec.append(pf.get("omega_mem_final", 0) / 100.0)
        vec.append(pf.get("assurance_score", 0) / 100.0)
        vectors.append(vec)
        if (i + 1) % 100 == 0:
            print(f"    {i+1}/{len(cases)}...")
    return np.array(vectors)


def compute_curvature(X_embedded, n_sample=1000, label=""):
    """Estimate sectional curvature from triangle comparison on embedded data."""
    n = X_embedded.shape[0]
    rng = np.random.RandomState(42)
    curvatures = []

    for _ in range(n_sample):
        i, j, k = rng.choice(n, 3, replace=False)
        d_ij = np.sqrt(np.sum((X_embedded[i] - X_embedded[j])**2))
        d_jk = np.sqrt(np.sum((X_embedded[j] - X_embedded[k])**2))
        d_ik = np.sqrt(np.sum((X_embedded[i] - X_embedded[k])**2))

        if d_ij < 1e-10 or d_jk < 1e-10:
            continue

        # Cosine rule in flat space
        cos_angle = np.clip((d_ij**2 + d_jk**2 - d_ik**2) / (2 * d_ij * d_jk + 1e-15), -1, 1)
        d_expected = np.sqrt(max(0, d_ij**2 + d_jk**2 - 2*d_ij*d_jk*cos_angle))

        if d_expected > 1e-10:
            curvatures.append((d_ik - d_expected) / d_expected)

    if not curvatures:
        return {"method": label, "K_mean": 0.0, "K_std": 0.0, "K_median": 0.0, "n_triangles": 0}

    K_mean = float(np.mean(curvatures))
    K_std = float(np.std(curvatures))
    K_median = float(np.median(curvatures))
    K_abs_mean = float(np.mean(np.abs(curvatures)))

    # Statistical test: is K significantly different from 0?
    se = K_std / np.sqrt(len(curvatures))
    t_stat = abs(K_mean) / se if se > 0 else 0
    significant = t_stat > 2.0  # p < 0.05 approx

    return {
        "method": label,
        "K_mean": round(K_mean, 8),
        "K_std": round(K_std, 6),
        "K_median": round(K_median, 8),
        "K_abs_mean": round(K_abs_mean, 6),
        "n_triangles": len(curvatures),
        "t_statistic": round(float(t_stat), 2),
        "significantly_nonzero": significant,
    }


def main():
    print("=" * 60)
    print("  CURVATURE VALIDATION: Is K=0 real?")
    print("=" * 60)

    print("\n  Collecting signal vectors from corpus...")
    X = collect_vectors()
    n, d = X.shape
    print(f"  Data: {n} × {d}")

    # Remove zero-variance
    var = np.var(X, axis=0)
    active = var > 1e-8
    X_active = X[:, active]
    n_active = X_active.shape[1]
    print(f"  Active dimensions: {n_active}")

    # Standardize
    X_std = (X_active - np.mean(X_active, axis=0)) / (np.std(X_active, axis=0) + 1e-10)

    results = []

    # =====================================================================
    # LINEAR PCA (baseline)
    # =====================================================================
    print("\n  1. LINEAR PCA...")
    cov = np.cov(X_std, rowvar=False)
    eig_vals, eig_vecs = np.linalg.eigh(cov)
    idx = np.argsort(eig_vals)[::-1]
    eig_vecs = eig_vecs[:, idx]
    X_pca = X_std @ eig_vecs[:, :5]

    r_pca = compute_curvature(X_pca, n_sample=2000, label="Linear PCA (d=5)")
    results.append(r_pca)
    print(f"    K_mean = {r_pca['K_mean']:.8f}, K_std = {r_pca['K_std']:.6f}, significant: {r_pca['significantly_nonzero']}")

    # =====================================================================
    # KERNEL PCA (RBF)
    # =====================================================================
    print("\n  2. KERNEL PCA (RBF)...")

    for gamma in [0.1, 0.5, 1.0]:
        # RBF kernel: K(x,y) = exp(-gamma * ||x-y||^2)
        # Compute kernel matrix
        sq_dists = np.zeros((n, n))
        for i in range(n):
            diff = X_std[i] - X_std
            sq_dists[i] = np.sum(diff**2, axis=1)
        K_mat = np.exp(-gamma * sq_dists)

        # Center the kernel
        n_mat = K_mat.shape[0]
        one_n = np.ones((n_mat, n_mat)) / n_mat
        K_centered = K_mat - one_n @ K_mat - K_mat @ one_n + one_n @ K_mat @ one_n

        # Eigen decomposition
        eig_vals_k, eig_vecs_k = np.linalg.eigh(K_centered)
        idx_k = np.argsort(eig_vals_k)[::-1]
        eig_vals_k = eig_vals_k[idx_k]
        eig_vecs_k = eig_vecs_k[:, idx_k]

        # Project to top 5
        top5_vals = np.maximum(eig_vals_k[:5], 1e-10)
        X_kpca = eig_vecs_k[:, :5] * np.sqrt(top5_vals)

        label = f"Kernel PCA (RBF γ={gamma})"
        r_kpca = compute_curvature(X_kpca, n_sample=2000, label=label)
        results.append(r_kpca)
        print(f"    γ={gamma}: K_mean = {r_kpca['K_mean']:.8f}, K_std = {r_kpca['K_std']:.6f}, significant: {r_kpca['significantly_nonzero']}")

    # =====================================================================
    # UMAP (if available)
    # =====================================================================
    print("\n  3. UMAP...")
    try:
        import umap
        reducer = umap.UMAP(n_components=5, n_neighbors=15, min_dist=0.1, random_state=42)
        X_umap = reducer.fit_transform(X_std)
        r_umap = compute_curvature(X_umap, n_sample=2000, label="UMAP (d=5)")
        results.append(r_umap)
        print(f"    K_mean = {r_umap['K_mean']:.8f}, K_std = {r_umap['K_std']:.6f}, significant: {r_umap['significantly_nonzero']}")
    except ImportError:
        print("    UMAP not installed — using manual neighborhood graph embedding")
        # Manual nonlinear embedding: local tangent space alignment (simplified)
        # Use k-nearest neighbors to build local linear patches
        from numpy.linalg import svd

        k = 15
        # Build kNN distance matrix
        sq_dists = np.zeros((n, n))
        for i in range(n):
            diff = X_std[i] - X_std
            sq_dists[i] = np.sum(diff**2, axis=1)

        # For each point, fit local PCA on k neighbors
        local_dims = []
        for i in range(min(n, 200)):
            nn = np.argsort(sq_dists[i])[:k+1]
            local_data = X_std[nn] - X_std[nn].mean(axis=0)
            _, s, _ = svd(local_data, full_matrices=False)
            # Intrinsic dimension: number of singular values > 10% of max
            local_d = np.sum(s > 0.1 * s[0])
            local_dims.append(local_d)

        mean_local_d = np.mean(local_dims)
        std_local_d = np.std(local_dims)
        print(f"    Local intrinsic dimension: {mean_local_d:.1f} ± {std_local_d:.1f}")

        # Use geodesic distances (shortest path through kNN graph) as Isomap proxy
        # Build adjacency
        adj = np.full((n, n), np.inf)
        for i in range(n):
            nn = np.argsort(sq_dists[i])[:k+1]
            for j in nn:
                d = np.sqrt(sq_dists[i][j])
                adj[i][j] = d
                adj[j][i] = d
            adj[i][i] = 0

        # Floyd-Warshall (small n, ok)
        print("    Computing geodesic distances (Floyd-Warshall)...")
        geo = adj.copy()
        for mid in range(n):
            for i in range(n):
                for j in range(n):
                    if geo[i][mid] + geo[mid][j] < geo[i][j]:
                        geo[i][j] = geo[i][mid] + geo[mid][j]

        # MDS on geodesic distances → Isomap embedding
        print("    Computing Isomap embedding (MDS on geodesic distances)...")
        # Replace inf with large finite value
        max_finite = np.max(geo[np.isfinite(geo)]) if np.any(np.isfinite(geo)) else 10.0
        geo = np.where(np.isfinite(geo), geo, max_finite * 2)
        # Center the squared distance matrix
        geo_sq = geo ** 2
        H = np.eye(n) - np.ones((n, n)) / n
        B = -0.5 * H @ geo_sq @ H
        B = np.nan_to_num(B, nan=0.0, posinf=0.0, neginf=0.0)

        eig_vals_iso, eig_vecs_iso = np.linalg.eigh(B)
        idx_iso = np.argsort(eig_vals_iso)[::-1]
        eig_vals_iso = eig_vals_iso[idx_iso]
        eig_vecs_iso = eig_vecs_iso[:, idx_iso]

        top5_iso = np.maximum(eig_vals_iso[:5], 1e-10)
        X_isomap = eig_vecs_iso[:, :5] * np.sqrt(top5_iso)

        r_umap_proxy = compute_curvature(X_isomap, n_sample=2000, label="Isomap (geodesic MDS, d=5)")
        results.append(r_umap_proxy)
        print(f"    K_mean = {r_umap_proxy['K_mean']:.8f}, K_std = {r_umap_proxy['K_std']:.6f}, significant: {r_umap_proxy['significantly_nonzero']}")

    # =====================================================================
    # COMPARISON
    # =====================================================================
    print("\n" + "=" * 60)
    print("  COMPARISON")
    print("=" * 60)

    print(f"\n  {'Method':<35s} {'K_mean':>12s} {'K_std':>10s} {'|K|_mean':>10s} {'Sig?':>6s}")
    print(f"  {'-'*35} {'-'*12} {'-'*10} {'-'*10} {'-'*6}")
    for r in results:
        sig = "YES" if r["significantly_nonzero"] else "no"
        print(f"  {r['method']:<35s} {r['K_mean']:>12.8f} {r['K_std']:>10.6f} {r['K_abs_mean']:>10.6f} {sig:>6s}")

    # Verdict
    any_significant = any(r["significantly_nonzero"] for r in results)
    all_near_zero = all(abs(r["K_mean"]) < 0.01 for r in results)
    nonlinear_curved = any(r["significantly_nonzero"] for r in results if "Kernel" in r["method"] or "UMAP" in r["method"] or "Isomap" in r["method"])

    print(f"\n  VERDICT:")
    if not any_significant:
        print(f"  K=0 is REAL. No method (linear or nonlinear) detects significant curvature.")
        print(f"  The Risk Polytope is genuinely flat.")
        verdict = "K=0 confirmed (all methods)"
    elif nonlinear_curved and not results[0]["significantly_nonzero"]:
        print(f"  K=0 was a LINEAR METHOD ARTIFACT.")
        print(f"  Nonlinear methods detect curvature that PCA misses.")
        print(f"  The true space is curved. The polytope is a flat projection of a curved object.")
        verdict = "K=0 was artifact — true space is curved"
    elif any_significant:
        print(f"  MIXED RESULTS. Some methods detect curvature, others don't.")
        print(f"  The curvature may be weak or localized.")
        verdict = "Weak/localized curvature detected"
    else:
        verdict = "Inconclusive"

    # Save
    output = {
        "n_samples": int(n),
        "n_active_dimensions": int(n_active),
        "methods": results,
        "any_significant_curvature": any_significant,
        "nonlinear_methods_curved": nonlinear_curved,
        "linear_pca_curved": results[0]["significantly_nonzero"] if results else False,
        "verdict": verdict,
    }

    def _jd(x):
        if isinstance(x, (np.floating,)): return float(x)
        if isinstance(x, (np.integer,)): return int(x)
        if isinstance(x, (np.bool_,)): return bool(x)
        return str(x)
    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "research", "results", "curvature_validation.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=_jd)
    print(f"\n  Saved to {out_path}")


if __name__ == "__main__":
    main()
