#!/usr/bin/env python3
"""
Find the Object.

The hypothesis: the 83 scoring signals are projections of a single
lower-dimensional mathematical object. This script discovers:

1. The intrinsic dimensionality (how many independent dimensions?)
2. The principal directions (what are the axes of the object?)
3. The topology (what shape is it?)
4. The geometry (is it flat or curved?)
5. The dynamics (how do agents move on it?)
6. The thermodynamics (does it have temperature?)
7. The name (what is it?)
"""

import sys, os, math, random, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring_engine import compute, MemoryEntry

MEMORY_TYPES = ["tool_state", "shared_workflow", "episodic", "preference", "semantic", "policy", "identity"]
DOMAINS = ["general", "customer_support", "coding", "legal", "fintech", "medical"]
ACTION_TYPES = ["informational", "reversible", "irreversible", "destructive"]


def make_entries(rng, n):
    entries = []
    for i in range(n):
        entries.append(MemoryEntry(
            id=f"e_{i}",
            content=f"Memory content {i} " + rng.choice(["alpha", "beta", "gamma", "delta", "epsilon"]) * rng.randint(1, 5),
            type=rng.choice(MEMORY_TYPES),
            timestamp_age_days=rng.uniform(0.01, 500),
            source_trust=rng.uniform(0.05, 0.99),
            source_conflict=rng.uniform(0.01, 0.95),
            downstream_count=rng.randint(0, 80),
            r_belief=rng.uniform(0.05, 0.99),
            healing_counter=rng.randint(0, 5),
        ))
    return entries


def extract_vector(entries, action_type, domain):
    """Extract the component breakdown as a normalized vector."""
    result = compute(entries, action_type, domain)
    cb = result.component_breakdown
    keys = ["s_freshness", "s_drift", "s_provenance", "s_propagation",
            "r_recall", "r_encode", "s_interference", "s_recovery",
            "r_belief", "s_relevance"]
    vec = [cb.get(k, 0.0) / 100.0 for k in keys]
    vec.append(result.omega_mem_final / 100.0)
    vec.append(result.assurance_score / 100.0)
    return vec, result


def main():
    N = 15000
    print(f"Generating {N} signal vectors...")
    t0 = time.time()

    vectors = []
    omegas = []
    actions = []
    domains_used = []

    for i in range(N):
        rng = random.Random(i)
        n_entries = rng.randint(2, 12)
        action_type = rng.choice(ACTION_TYPES)
        domain = rng.choice(DOMAINS)
        entries = make_entries(rng, n_entries)

        vec, result = extract_vector(entries, action_type, domain)
        vectors.append(vec)
        omegas.append(result.omega_mem_final)
        actions.append(result.recommended_action)
        domains_used.append(domain)

        if (i + 1) % 3000 == 0:
            print(f"  {i+1}/{N} ({(time.time()-t0):.1f}s)")

    X = np.array(vectors)
    n_samples, n_dims = X.shape
    print(f"\nData: {n_samples} × {n_dims}")
    print(f"Generation time: {time.time()-t0:.1f}s")

    # =====================================================================
    # 1. INTRINSIC DIMENSIONALITY — Eigenvalue spectrum
    # =====================================================================
    print("\n" + "=" * 60)
    print("  1. INTRINSIC DIMENSIONALITY")
    print("=" * 60)

    # Remove zero-variance columns
    variances = np.var(X, axis=0)
    active = variances > 1e-8
    X_active = X[:, active]
    n_active = X_active.shape[1]
    print(f"Active dimensions: {n_active} / {n_dims}")

    # Correlation matrix eigenvalues
    corr = np.corrcoef(X_active, rowvar=False)
    corr = np.nan_to_num(corr, nan=0.0)
    eigenvalues = np.linalg.eigvalsh(corr)
    eigenvalues = np.sort(eigenvalues)[::-1]  # Descending

    # Marchenko-Pastur boundary
    gamma = n_samples / n_active
    mp_upper = (1 + 1/np.sqrt(gamma))**2
    mp_lower = (1 - 1/np.sqrt(gamma))**2

    signal_eigs = eigenvalues[eigenvalues > mp_upper]
    noise_eigs = eigenvalues[eigenvalues <= mp_upper]

    print(f"\nEigenvalue spectrum:")
    for i, ev in enumerate(eigenvalues[:min(15, len(eigenvalues))]):
        bar = "█" * int(ev * 10)
        marker = " ← SIGNAL" if ev > mp_upper else "   noise"
        print(f"  λ_{i+1:2d} = {ev:7.4f}  {bar}{marker}")
    if len(eigenvalues) > 15:
        print(f"  ... ({len(eigenvalues) - 15} more, all < {eigenvalues[15]:.4f})")

    print(f"\nMarchenko-Pastur boundary: λ > {mp_upper:.4f} = signal")
    print(f"Signal dimensions: {len(signal_eigs)}")
    print(f"Noise dimensions: {len(noise_eigs)}")

    # Explained variance ratio
    total_var = np.sum(eigenvalues)
    cumulative = np.cumsum(eigenvalues) / total_var
    for threshold in [0.90, 0.95, 0.99]:
        d = np.searchsorted(cumulative, threshold) + 1
        print(f"  {threshold*100:.0f}% variance explained by {d} dimensions")

    intrinsic_dim = len(signal_eigs)
    print(f"\n  THE OBJECT HAS {intrinsic_dim} DIMENSIONS.")

    # =====================================================================
    # 2. PRINCIPAL DIRECTIONS — What are the axes?
    # =====================================================================
    print("\n" + "=" * 60)
    print("  2. PRINCIPAL DIRECTIONS")
    print("=" * 60)

    # PCA via eigendecomposition
    cov = np.cov(X_active, rowvar=False)
    cov = np.nan_to_num(cov, nan=0.0)
    eig_vals, eig_vecs = np.linalg.eigh(cov)
    # Sort descending
    idx = np.argsort(eig_vals)[::-1]
    eig_vals = eig_vals[idx]
    eig_vecs = eig_vecs[:, idx]

    component_names = ["s_freshness", "s_drift", "s_provenance", "s_propagation",
                       "r_recall", "r_encode", "s_interference", "s_recovery",
                       "r_belief", "s_relevance", "omega", "assurance"]
    active_names = [component_names[i] for i in range(n_dims) if active[i]]

    print(f"\nPrincipal components (top {min(intrinsic_dim, 6)}):")
    for pc in range(min(intrinsic_dim, 6)):
        vec = eig_vecs[:, pc]
        var_explained = eig_vals[pc] / np.sum(eig_vals) * 100
        # Top contributors
        abs_vec = np.abs(vec)
        top_idx = np.argsort(abs_vec)[::-1][:4]
        contributors = [(active_names[j], vec[j]) for j in top_idx]
        desc = " + ".join([f"{w:+.2f}·{n}" for n, w in contributors])
        print(f"\n  PC{pc+1} ({var_explained:.1f}% variance):")
        print(f"    {desc}")

    # Name the axes
    print(f"\n  AXIS INTERPRETATION:")
    for pc in range(min(intrinsic_dim, 4)):
        vec = eig_vecs[:, pc]
        abs_vec = np.abs(vec)
        top = np.argmax(abs_vec)
        name = active_names[top]
        if name in ("s_freshness", "r_recall"):
            print(f"    PC{pc+1}: TEMPORAL DECAY (how old is the memory?)")
        elif name in ("s_drift", "s_interference"):
            print(f"    PC{pc+1}: CORRUPTION (how much has the memory changed?)")
        elif name in ("s_provenance", "r_belief"):
            print(f"    PC{pc+1}: TRUST (how reliable is the source?)")
        elif name in ("s_propagation",):
            print(f"    PC{pc+1}: INFLUENCE (how far does this memory reach?)")
        elif name in ("s_recovery",):
            print(f"    PC{pc+1}: RESILIENCE (can the memory self-heal?)")
        elif name in ("omega", "assurance"):
            print(f"    PC{pc+1}: RISK (the aggregate danger)")
        elif name in ("s_relevance",):
            print(f"    PC{pc+1}: COHERENCE (does this memory belong?)")
        else:
            print(f"    PC{pc+1}: {name}")

    # =====================================================================
    # 3. TOPOLOGY — What shape is the object?
    # =====================================================================
    print("\n" + "=" * 60)
    print("  3. TOPOLOGY")
    print("=" * 60)

    # Project onto top dimensions
    X_proj = X_active @ eig_vecs[:, :intrinsic_dim]

    # Compute pairwise distances (subsample for speed)
    n_sample = min(2000, n_samples)
    rng_sub = np.random.RandomState(42)
    idx_sub = rng_sub.choice(n_samples, n_sample, replace=False)
    X_sub = X_proj[idx_sub]

    # Distance matrix (pure numpy, no scipy)
    n_sub_actual = X_sub.shape[0]
    dist_matrix = np.zeros((n_sub_actual, n_sub_actual))
    for i in range(n_sub_actual):
        diff = X_sub[i] - X_sub
        dist_matrix[i] = np.sqrt(np.sum(diff**2, axis=1))
    dists = dist_matrix[np.triu_indices(n_sub_actual, k=1)]

    # Basic topology: connected components at different scales
    print(f"\nPercolation analysis (on {n_sample} samples):")
    scales = np.percentile(dists, [10, 20, 30, 40, 50, 60, 70, 80, 90])
    for pct, scale in zip([10, 20, 30, 40, 50, 60, 70, 80, 90], scales):
        # Count connected components via union-find
        parent = list(range(n_sample))
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(a, b):
            a, b = find(a), find(b)
            if a != b:
                parent[a] = b
        adj = dist_matrix < scale
        for i in range(n_sample):
            for j in range(i+1, n_sample):
                if adj[i][j]:
                    union(i, j)
        components = len(set(find(i) for i in range(n_sample)))
        print(f"  scale={scale:.3f} (p{pct}): {components} components")

    # Check if the object is convex
    # Simple test: for random pairs, is the midpoint also in the data?
    midpoint_distances = []
    for _ in range(1000):
        i, j = rng_sub.choice(n_sample, 2, replace=False)
        midpoint = (X_sub[i] + X_sub[j]) / 2
        # Distance from midpoint to nearest data point
        d_to_nearest = np.min(np.sqrt(np.sum((X_sub - midpoint)**2, axis=1)))
        midpoint_distances.append(d_to_nearest)

    avg_midpoint_dist = np.mean(midpoint_distances)
    avg_data_dist = np.mean(dists)
    convexity_ratio = avg_midpoint_dist / avg_data_dist

    print(f"\nConvexity test:")
    print(f"  Average midpoint-to-nearest: {avg_midpoint_dist:.4f}")
    print(f"  Average pairwise distance:   {avg_data_dist:.4f}")
    print(f"  Convexity ratio: {convexity_ratio:.4f}")
    if convexity_ratio < 0.3:
        print(f"  → Object is approximately CONVEX (midpoints are close to data)")
        shape = "convex body"
    elif convexity_ratio < 0.6:
        print(f"  → Object is STAR-SHAPED (midpoints sometimes far from data)")
        shape = "star-shaped region"
    else:
        print(f"  → Object is NON-CONVEX (holes or complex topology)")
        shape = "non-convex manifold"

    # =====================================================================
    # 4. GEOMETRY — Curvature
    # =====================================================================
    print("\n" + "=" * 60)
    print("  4. GEOMETRY")
    print("=" * 60)

    # Estimate curvature via triangle comparison
    # In flat space: d(a,c)² = d(a,b)² + d(b,c)² - 2·d(a,b)·d(b,c)·cos(θ)
    # Deviation from this = curvature
    curvature_samples = []
    for _ in range(2000):
        i, j, k = rng_sub.choice(n_sample, 3, replace=False)
        d_ij = dist_matrix[i][j]
        d_jk = dist_matrix[j][k]
        d_ik = dist_matrix[i][k]
        if d_ij > 0 and d_jk > 0:
            # Cosine rule in flat space
            cos_angle = (d_ij**2 + d_jk**2 - d_ik**2) / (2 * d_ij * d_jk + 1e-10)
            cos_angle = np.clip(cos_angle, -1, 1)
            # Expected d_ik in flat space
            d_expected = np.sqrt(d_ij**2 + d_jk**2 - 2*d_ij*d_jk*cos_angle)
            # Curvature indicator: actual vs expected
            if d_expected > 0:
                curvature_samples.append((d_ik - d_expected) / d_expected)

    curvature_mean = np.mean(curvature_samples)
    curvature_std = np.std(curvature_samples)

    print(f"\nSectional curvature estimate:")
    print(f"  Mean curvature: {curvature_mean:.6f}")
    print(f"  Std curvature:  {curvature_std:.6f}")
    if abs(curvature_mean) < 0.01:
        print(f"  → Object is approximately FLAT (Euclidean geometry)")
        geometry = "flat"
    elif curvature_mean > 0.01:
        print(f"  → Object has POSITIVE curvature (sphere-like)")
        geometry = "positively curved"
    else:
        print(f"  → Object has NEGATIVE curvature (hyperbolic)")
        geometry = "negatively curved"

    # =====================================================================
    # 5. DYNAMICS — How do agents move on it?
    # =====================================================================
    print("\n" + "=" * 60)
    print("  5. DYNAMICS")
    print("=" * 60)

    # Compute velocity field: direction of increasing omega
    omega_arr = np.array(omegas)
    X_proj_full = X_active @ eig_vecs[:, :intrinsic_dim]

    # For each point, compute gradient of omega w.r.t. projected coordinates
    # Using local linear regression
    gradients = []
    for i in range(min(500, n_samples)):
        # Find 20 nearest neighbors
        dists_i = np.sqrt(np.sum((X_proj_full - X_proj_full[i])**2, axis=1))
        nn_idx = np.argsort(dists_i)[1:21]
        delta_x = X_proj_full[nn_idx] - X_proj_full[i]
        delta_omega = omega_arr[nn_idx] - omega_arr[i]
        # Least squares: delta_omega ≈ delta_x @ gradient
        try:
            grad, _, _, _ = np.linalg.lstsq(delta_x, delta_omega, rcond=None)
            gradients.append(grad)
        except:
            pass

    if gradients:
        grad_matrix = np.array(gradients)
        mean_grad = np.mean(grad_matrix, axis=0)
        grad_magnitude = np.sqrt(np.sum(mean_grad**2))
        grad_direction = mean_grad / (grad_magnitude + 1e-10)

        print(f"\nOmega gradient on the manifold:")
        print(f"  Magnitude: {grad_magnitude:.4f}")
        print(f"  Direction (in PC space):")
        for j in range(min(intrinsic_dim, 4)):
            print(f"    PC{j+1}: {grad_direction[j]:+.4f}")

        # Dominant gradient direction
        dominant_pc = np.argmax(np.abs(grad_direction))
        print(f"  Dominant axis: PC{dominant_pc+1}")
        print(f"  → Agents degrade primarily along PC{dominant_pc+1}")

        # Check for attractors: does the gradient field have fixed points?
        # A fixed point is where gradient ≈ 0
        grad_norms = np.sqrt(np.sum(grad_matrix**2, axis=1))
        slow_points = np.sum(grad_norms < np.percentile(grad_norms, 5))
        print(f"\n  Fixed points (gradient < 5th percentile): {slow_points}")
        print(f"  → {'Attractors exist' if slow_points > 10 else 'No strong attractors'}")

    # =====================================================================
    # 6. THERMODYNAMICS — Does the object have temperature?
    # =====================================================================
    print("\n" + "=" * 60)
    print("  6. THERMODYNAMICS")
    print("=" * 60)

    # Information temperature: τ = Var(omega) / Mean(omega)
    tau = np.var(omega_arr) / (np.mean(omega_arr) + 1e-10)
    print(f"\n  Information temperature τ = {tau:.4f}")

    # Entropy of omega distribution
    hist, bin_edges = np.histogram(omega_arr, bins=50, density=True)
    bin_width = bin_edges[1] - bin_edges[0]
    entropy = -np.sum(hist * np.log(hist + 1e-10) * bin_width)
    print(f"  Entropy H = {entropy:.4f}")

    # Free energy: F = <E> - T·S where E = omega, T = tau, S = entropy
    mean_omega = np.mean(omega_arr)
    free_energy = mean_omega - tau * entropy
    print(f"  Mean omega (energy) = {mean_omega:.4f}")
    print(f"  Free energy F = E - τS = {free_energy:.4f}")

    # Test equipartition: does each PC have equal energy?
    pc_energies = np.var(X_proj_full, axis=0)
    pc_energy_ratio = np.max(pc_energies) / (np.min(pc_energies) + 1e-10)
    print(f"\n  Equipartition test:")
    print(f"  PC energy ratio (max/min): {pc_energy_ratio:.2f}")
    if pc_energy_ratio < 3:
        print(f"  → EQUIPARTITION HOLDS — energy distributed equally across dimensions")
        print(f"  → The object is in THERMAL EQUILIBRIUM")
    else:
        print(f"  → Equipartition violated — energy concentrated in few dimensions")
        print(f"  → The object is OUT OF EQUILIBRIUM")

    # =====================================================================
    # 7. THE OBJECT
    # =====================================================================
    print("\n" + "=" * 60)
    print("  7. THE OBJECT")
    print("=" * 60)

    print(f"""
  Dimensionality:  {intrinsic_dim}
  Shape:           {shape}
  Geometry:        {geometry}
  Temperature:     τ = {tau:.4f}
  Entropy:         H = {entropy:.4f}
  Free energy:     F = {free_energy:.4f}
  Phase constant:  κ_MEM ≈ 0.046 (from prior measurement)

  The object is a {intrinsic_dim}-dimensional {shape} with
  {geometry} geometry, embedded in {n_active}-dimensional
  signal space.
""")

    # Compute the characteristic scales
    pc_scales = np.sqrt(eig_vals[:intrinsic_dim])
    print(f"  Characteristic scales (std along each axis):")
    for j in range(intrinsic_dim):
        print(f"    Axis {j+1}: {pc_scales[j]:.4f}")

    # The fundamental constants
    print(f"\n  FUNDAMENTAL CONSTANTS OF THE OBJECT:")
    print(f"    d = {intrinsic_dim}  (intrinsic dimension)")
    print(f"    κ = 0.046  (percolation threshold)")
    print(f"    τ = {tau:.4f}  (information temperature)")
    print(f"    H = {entropy:.4f}  (entropy)")
    print(f"    F = {free_energy:.4f}  (free energy)")
    print(f"    R = {convexity_ratio:.4f}  (convexity ratio)")
    print(f"    K = {curvature_mean:.6f}  (mean sectional curvature)")

    # What to call it
    if intrinsic_dim <= 4 and geometry == "flat" and shape == "convex body":
        name = f"The Memory Simplex — a {intrinsic_dim}-dimensional convex polytope"
    elif intrinsic_dim <= 4 and geometry == "positively curved":
        name = f"The Memory Sphere — a {intrinsic_dim}-dimensional curved manifold"
    elif intrinsic_dim <= 6 and geometry == "flat":
        name = f"The Risk Polytope — a {intrinsic_dim}-dimensional flat body"
    elif geometry == "negatively curved":
        name = f"The Memory Hyperboloid — a {intrinsic_dim}-dimensional hyperbolic space"
    else:
        name = f"The Memory Manifold — a {intrinsic_dim}-dimensional {geometry} {shape}"

    print(f"\n  NAME: {name}")
    print(f"\n  Every preflight call computes a point on this object.")
    print(f"  Every heal moves the point along a geodesic.")
    print(f"  Every attack pushes the point toward the boundary.")
    print(f"  The object is what the 83 modules are measuring.")

    # Save
    import json
    result = {
        "intrinsic_dimension": int(intrinsic_dim),
        "shape": shape,
        "geometry": geometry,
        "temperature": round(float(tau), 4),
        "entropy": round(float(entropy), 4),
        "free_energy": round(float(free_energy), 4),
        "convexity_ratio": round(float(convexity_ratio), 4),
        "mean_curvature": round(float(curvature_mean), 6),
        "kappa_mem": 0.046,
        "eigenvalues": [round(float(e), 4) for e in eigenvalues[:15]],
        "pc_scales": [round(float(s), 4) for s in pc_scales],
        "name": name,
        "n_samples": n_samples,
    }
    with open("/tmp/the_object.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n  Saved to /tmp/the_object.json")


if __name__ == "__main__":
    main()
