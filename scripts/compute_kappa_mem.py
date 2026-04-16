#!/usr/bin/env python3
"""
Compute κ_MEM — the Memory Phase Constant.

κ_MEM is the percolation threshold of the signal correlation graph:
the critical correlation threshold t* where the graph of scoring signals
transitions from connected to disconnected.

Steps:
1. Generate 10,000 signal vectors from the scoring engine using diverse synthetic agents
2. Build the Pearson correlation matrix across all signal dimensions
3. Sweep thresholds t = 0.00, 0.01, ... 1.00 — at each, build adjacency A[i,j] = 1 if |corr[i,j]| > t
4. Compute Fiedler value lambda_2 (second-smallest eigenvalue of graph Laplacian) at each t
5. Find t* where lambda_2 transitions from >0 (connected) to =0 (disconnected)
6. Validate stability: split-half consistency

Output: κ_MEM to 4 decimal places, stability check, phase transition curve.
"""

import sys, os, math, random, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring_engine import compute, MemoryEntry
from scoring_engine.drift_detector import compute_drift_metrics
from scoring_engine.calibration import compute_calibration
from scoring_engine.hawkes_process import hawkes_from_entries
from scoring_engine.copula import compute_copula
from scoring_engine.mewma import compute_mewma
from scoring_engine.consolidation import compute_consolidation
from scoring_engine.free_energy import compute_free_energy
from scoring_engine.mahalanobis import compute_mahalanobis
from scoring_engine.mutual_information import compute_mutual_information
from scoring_engine.spectral import compute_spectral
from scoring_engine.provenance_entropy import compute_provenance_entropy
from scoring_engine.stability_score import compute_stability_score, compute_r_total
from scoring_engine.info_thermodynamics import compute_info_thermodynamics


# ---------------------------------------------------------------------------
# Signal extraction: pull all continuous numerical outputs from a preflight
# ---------------------------------------------------------------------------

MEMORY_TYPES = ["tool_state", "shared_workflow", "episodic", "preference", "semantic", "policy", "identity"]
DOMAINS = ["general", "customer_support", "coding", "legal", "fintech", "medical"]
ACTION_TYPES = ["informational", "reversible", "irreversible", "destructive"]


def _make_entries(rng: random.Random, n: int) -> list:
    """Generate n diverse memory entries."""
    entries = []
    for i in range(n):
        mtype = rng.choice(MEMORY_TYPES)
        entries.append(MemoryEntry(
            id=f"e_{i}",
            content=f"Memory content {i} " + rng.choice(["alpha", "beta", "gamma", "delta"]) * rng.randint(1, 5),
            type=mtype,
            timestamp_age_days=rng.uniform(0.01, 500),
            source_trust=rng.uniform(0.05, 0.99),
            source_conflict=rng.uniform(0.01, 0.95),
            downstream_count=rng.randint(0, 80),
            r_belief=rng.uniform(0.05, 0.99),
            healing_counter=rng.randint(0, 5),
        ))
    return entries


def _val(obj, key, default=0.0):
    """Extract a value from a dict or dataclass-like object."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def extract_signal_vector(entries: list, action_type: str, domain: str) -> list:
    """Run scoring engine + analytics modules, return flat signal vector (all floats, normalized 0-1)."""
    signals = []

    # 1. Core omega scoring (10 components + omega + assurance)
    result = compute(entries, action_type, domain)
    cb = result.component_breakdown
    for key in ["s_freshness", "s_drift", "s_provenance", "s_propagation",
                "r_recall", "r_encode", "s_interference", "s_recovery",
                "r_belief", "s_relevance"]:
        signals.append(cb.get(key, 0.0) / 100.0)
    signals.append(result.omega_mem_final / 100.0)
    signals.append(result.assurance_score / 100.0)

    # 2. Drift metrics
    try:
        dm = compute_drift_metrics(entries)
        if dm:
            signals.append(dm.get("kl_divergence", 0) / 100.0)
            signals.append(dm.get("wasserstein", 0) / 100.0)
            signals.append(dm.get("jsd", 0) / 100.0)
            signals.append(dm.get("ensemble_score", 0) / 100.0)
        else:
            signals.extend([0.0] * 4)
    except Exception:
        signals.extend([0.0] * 4)

    # 3. Calibration
    try:
        cal = compute_calibration(cb)
        if cal:
            signals.append(min(1.0, cal.get("brier_score", 0)))
            signals.append(min(1.0, cal.get("meta_score", 0) / 100.0))
        else:
            signals.extend([0.0] * 2)
    except Exception:
        signals.extend([0.0] * 2)

    # 4. Hawkes
    try:
        hw = hawkes_from_entries(entries)
        if hw:
            signals.append(min(1.0, hw.get("current_lambda", 0) / 5.0))
            signals.append(1.0 if hw.get("burst_detected", False) else 0.0)
        else:
            signals.extend([0.0] * 2)
    except Exception:
        signals.extend([0.0] * 2)

    # 5. Copula
    try:
        cop = compute_copula(entries)
        if cop:
            signals.append((cop.rho + 1.0) / 2.0 if hasattr(cop, "rho") else 0.5)
            signals.append(min(1.0, cop.joint_risk / 100.0) if hasattr(cop, "joint_risk") else 0.0)
        else:
            signals.extend([0.5, 0.0])
    except Exception:
        signals.extend([0.5, 0.0])

    # 6. MEWMA
    try:
        mw = compute_mewma(entries)
        if mw:
            signals.append(min(1.0, mw.T2_stat / 50.0) if hasattr(mw, "T2_stat") else 0.0)
            signals.append(1.0 if (hasattr(mw, "out_of_control") and mw.out_of_control) else 0.0)
        else:
            signals.extend([0.0] * 2)
    except Exception:
        signals.extend([0.0] * 2)

    # 7. Consolidation
    try:
        con = compute_consolidation(entries)
        if con:
            signals.append(con.get("mean_consolidation", 0.5) if isinstance(con, dict) else getattr(con, "mean_consolidation", 0.5))
        else:
            signals.append(0.5)
    except Exception:
        signals.append(0.5)

    # 8. Free energy
    try:
        fe = compute_free_energy(cb)
        if fe:
            signals.append(min(1.0, max(0.0, fe.get("surprise", 0) if isinstance(fe, dict) else getattr(fe, "surprise", 0))))
            signals.append(min(1.0, max(0.0, (fe.get("kl_divergence", 0) if isinstance(fe, dict) else getattr(fe, "kl_divergence", 0)) / 10.0)))
        else:
            signals.extend([0.0] * 2)
    except Exception:
        signals.extend([0.0] * 2)

    # 9. Mahalanobis
    try:
        mah = compute_mahalanobis(entries)
        if mah:
            md = mah.get("mean_distance", 0) if isinstance(mah, dict) else getattr(mah, "mean_distance", 0)
            signals.append(min(1.0, md / 10.0))
            ac = mah.get("anomaly_count", 0) if isinstance(mah, dict) else getattr(mah, "anomaly_count", 0)
            signals.append(min(1.0, ac / max(len(entries), 1)))
        else:
            signals.extend([0.0] * 2)
    except Exception:
        signals.extend([0.0] * 2)

    # 10. Mutual information
    try:
        mi = compute_mutual_information(entries)
        if mi:
            signals.append(mi.get("nmi_score", 0) if isinstance(mi, dict) else getattr(mi, "nmi_score", 0))
            signals.append(mi.get("information_loss", 0) if isinstance(mi, dict) else getattr(mi, "information_loss", 0))
        else:
            signals.extend([0.0] * 2)
    except Exception:
        signals.extend([0.0] * 2)

    # 11. Spectral
    try:
        sp = compute_spectral(entries)
        if sp:
            signals.append(min(1.0, (sp.get("fiedler_value", 0) if isinstance(sp, dict) else getattr(sp, "fiedler_value", 0)) / 5.0))
            signals.append(min(1.0, (sp.get("spectral_gap", 0) if isinstance(sp, dict) else getattr(sp, "spectral_gap", 0))))
            mt = sp.get("mixing_time_estimate", 1) if isinstance(sp, dict) else getattr(sp, "mixing_time_estimate", 1)
            signals.append(min(1.0, 1.0 / max(mt, 0.01)))
        else:
            signals.extend([0.0] * 3)
    except Exception:
        signals.extend([0.0] * 3)

    # 12. Stability score
    try:
        ss = compute_stability_score(
            delta_alpha=cb.get("s_drift", 0) / 100.0,
            p_transition=0.1,
            omega_drift=cb.get("s_drift", 0) / 100.0,
            omega_0=result.omega_mem_final / 100.0,
            lambda_2=0.5,
            hurst=0.5,
            h1_rank=0,
            tau_mix=10.0,
            d_geo_causal=0.5,
        )
        if ss:
            signals.append(ss.get("score", 0.5) if isinstance(ss, dict) else getattr(ss, "score", 0.5))
        else:
            signals.append(0.5)
    except Exception:
        signals.append(0.5)

    # 13. R_total
    try:
        rt = compute_r_total(
            delta_alpha=cb.get("s_drift", 0) / 50.0,
            beta=0.5,
            H=0.1,
            omega_0=result.omega_mem_final,
            lambda_2=0.5,
        )
        if rt is not None:
            signals.append(min(1.0, (rt if isinstance(rt, (int, float)) else getattr(rt, "r_total_normalized", 0)) / 5.0))
        else:
            signals.append(0.0)
    except Exception:
        signals.append(0.0)

    # 14. Info thermodynamics
    try:
        omegas = [cb.get("s_freshness", 50), cb.get("s_drift", 30), cb.get("s_provenance", 20)]
        it = compute_info_thermodynamics(omegas)
        if it:
            signals.append(min(1.0, (it.get("transfer_entropy", 0) if isinstance(it, dict) else getattr(it, "transfer_entropy", 0)) / 2.0))
            signals.append(min(1.0, max(0.0, (it.get("information_temperature", 0) if isinstance(it, dict) else getattr(it, "information_temperature", 0)) / 50.0)))
            signals.append(min(1.0, max(0.0, (it.get("entropy_production", 0) if isinstance(it, dict) else getattr(it, "entropy_production", 0)))))
            signals.append(max(0.0, (it.get("reversibility", 0) if isinstance(it, dict) else getattr(it, "reversibility", 0))))
        else:
            signals.extend([0.0] * 4)
    except Exception:
        signals.extend([0.0] * 4)

    # 15. Provenance entropy
    try:
        pe = compute_provenance_entropy(entries)
        if pe:
            signals.append(min(1.0, _val(pe, "mean_entropy", 0) / 3.0))
        else:
            signals.append(0.0)
    except Exception:
        signals.append(0.0)

    # 16. Raw entry statistics (always available, high diversity)
    n = len(entries)
    ages = [e.timestamp_age_days for e in entries]
    trusts = [e.source_trust for e in entries]
    conflicts = [e.source_conflict for e in entries]
    downstreams = [e.downstream_count for e in entries]
    beliefs = [e.r_belief for e in entries]

    signals.append(min(1.0, sum(ages) / max(n, 1) / 500.0))  # mean age normalized
    signals.append(min(1.0, (max(ages) - min(ages)) / 500.0) if n > 1 else 0.0)  # age range
    signals.append(sum(trusts) / max(n, 1))  # mean trust
    signals.append((max(trusts) - min(trusts)) if n > 1 else 0.0)  # trust spread
    signals.append(sum(conflicts) / max(n, 1))  # mean conflict
    signals.append((max(conflicts) - min(conflicts)) if n > 1 else 0.0)  # conflict spread
    signals.append(min(1.0, sum(downstreams) / max(n, 1) / 80.0))  # mean downstream normalized
    signals.append(sum(beliefs) / max(n, 1))  # mean belief
    signals.append((max(beliefs) - min(beliefs)) if n > 1 else 0.0)  # belief spread
    signals.append(min(1.0, n / 15.0))  # entry count normalized

    # Variance-based signals (second-order statistics)
    if n > 1:
        age_var = sum((a - sum(ages)/n)**2 for a in ages) / (n - 1)
        trust_var = sum((t - sum(trusts)/n)**2 for t in trusts) / (n - 1)
        conflict_var = sum((c - sum(conflicts)/n)**2 for c in conflicts) / (n - 1)
        signals.append(min(1.0, age_var / 25000.0))  # age variance
        signals.append(min(1.0, trust_var))  # trust variance
        signals.append(min(1.0, conflict_var))  # conflict variance
    else:
        signals.extend([0.0, 0.0, 0.0])

    # Cross-statistics (interactions between entry properties)
    trust_conflict_corr = 0.0
    if n > 1:
        mt, mc = sum(trusts)/n, sum(conflicts)/n
        num = sum((t - mt) * (c - mc) for t, c in zip(trusts, conflicts))
        dt = math.sqrt(sum((t - mt)**2 for t in trusts))
        dc = math.sqrt(sum((c - mc)**2 for c in conflicts))
        if dt > 0 and dc > 0:
            trust_conflict_corr = num / (dt * dc)
    signals.append((trust_conflict_corr + 1.0) / 2.0)  # normalized to [0,1]

    age_trust_corr = 0.0
    if n > 1:
        ma, mt2 = sum(ages)/n, sum(trusts)/n
        num2 = sum((a - ma) * (t - mt2) for a, t in zip(ages, trusts))
        da = math.sqrt(sum((a - ma)**2 for a in ages))
        dt2 = math.sqrt(sum((t - mt2)**2 for t in trusts))
        if da > 0 and dt2 > 0:
            age_trust_corr = num2 / (da * dt2)
    signals.append((age_trust_corr + 1.0) / 2.0)

    # Type distribution entropy
    type_counts = {}
    for e in entries:
        type_counts[e.type] = type_counts.get(e.type, 0) + 1
    type_entropy = 0.0
    for count in type_counts.values():
        p = count / n
        if p > 0:
            type_entropy -= p * math.log(p + 1e-10)
    signals.append(min(1.0, type_entropy / 2.0))  # normalized (max entropy ~ 1.95 for 7 types)

    # Action type encoding
    act_map = {"informational": 0.0, "reversible": 0.33, "irreversible": 0.67, "destructive": 1.0}
    signals.append(act_map.get(action_type, 0.5))

    # Domain encoding
    dom_map = {"general": 0.0, "customer_support": 0.17, "coding": 0.33, "legal": 0.50, "fintech": 0.67, "medical": 0.83}
    signals.append(dom_map.get(domain, 0.5))

    # Ensure all signals are valid floats in [0, 1]
    cleaned = []
    for s in signals:
        v = float(s) if isinstance(s, (int, float)) else 0.0
        if math.isnan(v) or math.isinf(v):
            v = 0.0
        cleaned.append(max(0.0, min(1.0, v)))

    return cleaned


# ---------------------------------------------------------------------------
# Phase transition computation
# ---------------------------------------------------------------------------

def compute_fiedler(adj_matrix: np.ndarray) -> float:
    """Compute Fiedler value (lambda_2) from adjacency matrix."""
    n = adj_matrix.shape[0]
    if n < 2:
        return 0.0
    degree = np.sum(adj_matrix, axis=1)
    laplacian = np.diag(degree) - adj_matrix
    eigenvalues = np.linalg.eigvalsh(laplacian)
    eigenvalues.sort()
    return float(eigenvalues[1]) if len(eigenvalues) > 1 else 0.0


def find_percolation_threshold(corr_matrix: np.ndarray, steps: int = 200) -> tuple:
    """Sweep thresholds and find where Fiedler value drops to 0."""
    n = corr_matrix.shape[0]
    abs_corr = np.abs(corr_matrix)
    np.fill_diagonal(abs_corr, 0)

    thresholds = np.linspace(0.0, 1.0, steps + 1)
    fiedler_values = []

    for t in thresholds:
        adj = (abs_corr > t).astype(float)
        lam2 = compute_fiedler(adj)
        fiedler_values.append(lam2)

    fiedler_values = np.array(fiedler_values)

    # Find critical threshold: last t where lambda_2 > epsilon before it drops to ~0
    epsilon = 1e-6
    kappa = 0.0
    for i in range(len(thresholds) - 1):
        if fiedler_values[i] > epsilon and fiedler_values[i + 1] <= epsilon:
            # Linear interpolation for precision
            f_a, f_b = fiedler_values[i], fiedler_values[i + 1]
            t_a, t_b = thresholds[i], thresholds[i + 1]
            if f_a - f_b > 0:
                kappa = t_a + (t_b - t_a) * (f_a - epsilon) / (f_a - f_b)
            else:
                kappa = t_a
            break
    else:
        # If never dropped to 0, find the steepest descent
        if fiedler_values[-1] > epsilon:
            kappa = 1.0  # Never disconnects
        else:
            # Find where gradient is steepest
            gradients = np.diff(fiedler_values)
            steepest = np.argmin(gradients)
            kappa = float(thresholds[steepest])

    return kappa, thresholds, fiedler_values


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    N_VECTORS = 10000
    print(f"Generating {N_VECTORS} signal vectors from scoring engine...")
    print()

    vectors = []
    dim = None
    t0 = time.time()

    for i in range(N_VECTORS):
        rng = random.Random(i)
        n_entries = rng.randint(2, 15)
        action_type = rng.choice(ACTION_TYPES)
        domain = rng.choice(DOMAINS)
        entries = _make_entries(rng, n_entries)

        vec = extract_signal_vector(entries, action_type, domain)
        if dim is None:
            dim = len(vec)
            print(f"Signal dimensionality: {dim}")
        elif len(vec) != dim:
            # Pad or truncate to consistent dimension
            vec = vec[:dim] + [0.0] * max(0, dim - len(vec))

        vectors.append(vec)

        if (i + 1) % 1000 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            print(f"  {i+1}/{N_VECTORS} vectors ({rate:.0f}/sec, {elapsed:.1f}s elapsed)")

    elapsed_total = time.time() - t0
    print(f"\nGeneration complete: {N_VECTORS} vectors x {dim} dimensions in {elapsed_total:.1f}s")

    # Convert to numpy
    X = np.array(vectors)  # shape: (N, D)

    # Save vectors
    np.save("/tmp/signal_vectors.npy", X)
    print(f"Saved to /tmp/signal_vectors.npy")

    # Remove zero-variance columns (constant signals add no information)
    variances = np.var(X, axis=0)
    active_cols = variances > 1e-8
    X_active = X[:, active_cols]
    n_active = X_active.shape[1]
    print(f"\nActive dimensions (non-constant): {n_active} / {dim}")

    # Compute Pearson correlation matrix
    print("Computing correlation matrix...")
    corr = np.corrcoef(X_active, rowvar=False)  # shape: (D_active, D_active)
    # Replace NaN with 0 (from zero-variance columns that slipped through)
    corr = np.nan_to_num(corr, nan=0.0)

    # Find percolation threshold
    print("Sweeping 200 thresholds for phase transition...\n")
    kappa_full, thresholds, fiedler_full = find_percolation_threshold(corr, steps=200)

    # Split-half validation
    X_a = np.array(vectors[:N_VECTORS // 2])[:, active_cols]
    X_b = np.array(vectors[N_VECTORS // 2:])[:, active_cols]

    corr_a = np.nan_to_num(np.corrcoef(X_a, rowvar=False), nan=0.0)
    corr_b = np.nan_to_num(np.corrcoef(X_b, rowvar=False), nan=0.0)

    kappa_a, _, fiedler_a = find_percolation_threshold(corr_a, steps=200)
    kappa_b, _, fiedler_b = find_percolation_threshold(corr_b, steps=200)

    stability = abs(kappa_a - kappa_b)
    stable = stability < 0.01

    # Print results
    print("=" * 60)
    print(f"  κ_MEM = {kappa_full:.4f}")
    print("=" * 60)
    print()
    print(f"  Split-half A (first 5,000):   κ = {kappa_a:.4f}")
    print(f"  Split-half B (second 5,000):  κ = {kappa_b:.4f}")
    print(f"  Full dataset (all 10,000):    κ = {kappa_full:.4f}")
    print(f"  |κ_A - κ_B| = {stability:.4f}  {'STABLE' if stable else 'UNSTABLE'}")
    print()

    # Phase transition curve (ASCII)
    print("Phase transition: lambda_2 vs threshold")
    print("-" * 60)
    max_f = max(fiedler_full) if max(fiedler_full) > 0 else 1.0
    for i in range(0, len(thresholds), 4):  # Every 4th point
        t = thresholds[i]
        f = fiedler_full[i]
        bar_len = int(40 * f / max_f) if max_f > 0 else 0
        marker = " <-- κ_MEM" if abs(t - kappa_full) < 0.015 else ""
        print(f"  t={t:.2f}  λ₂={f:6.3f}  {'█' * bar_len}{marker}")
    print("-" * 60)
    print()

    # Save detailed results
    results = {
        "kappa_mem": round(kappa_full, 4),
        "kappa_a": round(kappa_a, 4),
        "kappa_b": round(kappa_b, 4),
        "stability_delta": round(stability, 4),
        "stable": stable,
        "n_vectors": N_VECTORS,
        "n_dimensions": dim,
        "n_active_dimensions": n_active,
        "thresholds": [round(float(t), 4) for t in thresholds[::4]],
        "fiedler_values": [round(float(f), 4) for f in fiedler_full[::4]],
    }

    import json

    class _Encoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.bool_, np.integer)):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, bool):
                return int(obj)
            return super().default(obj)

    with open("/tmp/kappa_mem_results.json", "w") as f:
        json.dump(results, f, indent=2, cls=_Encoder)
    print(f"Detailed results saved to /tmp/kappa_mem_results.json")

    return kappa_full


if __name__ == "__main__":
    main()
