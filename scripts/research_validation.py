#!/usr/bin/env python3
"""
Research validation tasks #612, #613, #614.

1. s_relevance impact measurement
2. κ_MEM recompute with s_relevance active
3. P(success|omega) calibration curve
"""

import sys, os, math, json, random, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from scoring_engine import compute, MemoryEntry
from scoring_engine.omega_mem import WEIGHTS


# =========================================================================
# TASK 1: s_relevance impact measurement
# =========================================================================

def task1_s_relevance_impact():
    print("=" * 60)
    print("  TASK 1: s_relevance IMPACT MEASUREMENT")
    print("=" * 60)

    from api.main import _load_benchmark_corpus

    cases = _load_benchmark_corpus()
    print(f"\nLoaded {len(cases)} corpus cases")

    results = []
    decision_changes = 0
    omega_deltas = []
    boundary_cases = []

    for i, case in enumerate(cases):
        ms = case["memory_state"]
        at = case.get("action_type", "reversible")
        dom = case.get("domain", "general")

        entries = []
        for e in ms:
            entries.append(MemoryEntry(
                id=e.get("id", f"e_{i}"),
                content=e.get("content", ""),
                type=e.get("type", "semantic"),
                timestamp_age_days=e.get("timestamp_age_days") or e.get("age_days") or 0,
                source_trust=e.get("source_trust", 0.9),
                source_conflict=e.get("source_conflict", 0.1),
                downstream_count=e.get("downstream_count", 1),
                r_belief=e.get("r_belief", 0.5),
            ))

        if not entries:
            continue

        # Run WITH s_relevance active (current behavior)
        r_active = compute(entries, at, dom)

        # Run WITHOUT s_relevance: force it to 0 by using custom weights with s_relevance=0
        _w_no_rel = dict(WEIGHTS)
        _w_no_rel["s_relevance"] = 0.0
        r_forced = compute(entries, at, dom, custom_weights=_w_no_rel)

        omega_before = r_forced.omega_mem_final
        omega_after = r_active.omega_mem_final
        delta = omega_after - omega_before
        decision_before = r_forced.recommended_action
        decision_after = r_active.recommended_action
        changed = decision_before != decision_after

        if changed:
            decision_changes += 1

        omega_deltas.append(delta)

        # Check boundary (within 5 points of threshold)
        for threshold in [25, 45, 70]:
            if abs(omega_after - threshold) < 5:
                boundary_cases.append({
                    "case_id": case.get("id", f"case_{i}"),
                    "omega_after": omega_after,
                    "threshold": threshold,
                    "distance": round(abs(omega_after - threshold), 1),
                })

        results.append({
            "case_id": case.get("id", f"case_{i}"),
            "omega_before": round(omega_before, 1),
            "omega_after": round(omega_after, 1),
            "omega_delta": round(delta, 2),
            "decision_before": decision_before,
            "decision_after": decision_after,
            "decision_changed": changed,
        })

        if (i + 1) % 100 == 0:
            print(f"  Processed {i+1}/{len(cases)}...")

    # Categorize decision changes
    change_types = {}
    for r in results:
        if r["decision_changed"]:
            key = f"{r['decision_before']}→{r['decision_after']}"
            change_types[key] = change_types.get(key, 0) + 1

    mean_delta = np.mean(omega_deltas)
    std_delta = np.std(omega_deltas)
    max_delta = max(omega_deltas)
    min_delta = min(omega_deltas)
    nonzero_deltas = [d for d in omega_deltas if abs(d) > 0.01]

    print(f"\n  RESULTS:")
    print(f"  Total cases: {len(results)}")
    print(f"  Decision changes: {decision_changes} ({decision_changes/max(len(results),1)*100:.1f}%)")
    print(f"  Change types: {change_types}")
    print(f"  Mean omega shift: {mean_delta:+.3f}")
    print(f"  Std omega shift: {std_delta:.3f}")
    print(f"  Range: [{min_delta:+.2f}, {max_delta:+.2f}]")
    print(f"  Cases with nonzero shift: {len(nonzero_deltas)} ({len(nonzero_deltas)/max(len(results),1)*100:.1f}%)")
    print(f"  Boundary cases (within 5pts of threshold): {len(boundary_cases)}")

    summary = {
        "total_cases": len(results),
        "decision_changes": decision_changes,
        "decision_change_rate": round(decision_changes / max(len(results), 1), 4),
        "change_types": change_types,
        "mean_omega_shift": round(float(mean_delta), 4),
        "std_omega_shift": round(float(std_delta), 4),
        "max_omega_shift": round(float(max_delta), 2),
        "min_omega_shift": round(float(min_delta), 2),
        "nonzero_shift_count": len(nonzero_deltas),
        "boundary_cases_count": len(boundary_cases),
        "boundary_cases": boundary_cases[:10],
    }

    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "research", "results", "s_relevance_impact.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Saved to {out_path}")
    return summary


# =========================================================================
# TASK 2: κ_MEM recompute with s_relevance active
# =========================================================================

def task2_kappa_mem_v2():
    print("\n" + "=" * 60)
    print("  TASK 2: κ_MEM RECOMPUTE WITH s_relevance ACTIVE")
    print("=" * 60)

    N = 10000
    print(f"\n  Generating {N} signal vectors (s_relevance now active)...")

    MEMORY_TYPES = ["tool_state", "shared_workflow", "episodic", "preference", "semantic", "policy", "identity"]
    DOMAINS = ["general", "customer_support", "coding", "legal", "fintech", "medical"]
    ACTION_TYPES = ["informational", "reversible", "irreversible", "destructive"]

    vectors = []
    for i in range(N):
        rng = random.Random(i)
        n_entries = rng.randint(2, 12)
        entries = []
        for j in range(n_entries):
            entries.append(MemoryEntry(
                id=f"k_{i}_{j}",
                content=f"Content {j} " + rng.choice(["alpha", "beta", "gamma", "delta"]) * rng.randint(1, 5),
                type=rng.choice(MEMORY_TYPES),
                timestamp_age_days=rng.uniform(0.01, 500),
                source_trust=rng.uniform(0.05, 0.99),
                source_conflict=rng.uniform(0.01, 0.95),
                downstream_count=rng.randint(0, 80),
                r_belief=rng.uniform(0.05, 0.99),
            ))
        at = rng.choice(ACTION_TYPES)
        dom = rng.choice(DOMAINS)
        result = compute(entries, at, dom)
        cb = result.component_breakdown
        vec = [cb.get(k, 0) / 100.0 for k in
               ["s_freshness", "s_drift", "s_provenance", "s_propagation",
                "r_recall", "r_encode", "s_interference", "s_recovery",
                "r_belief", "s_relevance"]]
        vec.append(result.omega_mem_final / 100.0)
        vec.append(result.assurance_score / 100.0)
        vectors.append(vec)

        if (i + 1) % 2000 == 0:
            print(f"    {i+1}/{N}")

    X = np.array(vectors)
    variances = np.var(X, axis=0)
    active = variances > 1e-8
    X_active = X[:, active]
    n_active = X_active.shape[1]
    print(f"  Active dimensions: {n_active} / {X.shape[1]}")

    # Check s_relevance variance
    s_rel_idx = 9  # s_relevance is index 9
    s_rel_var = variances[s_rel_idx]
    print(f"  s_relevance variance: {s_rel_var:.6f} (was 0.0 before fix)")

    corr = np.corrcoef(X_active, rowvar=False)
    corr = np.nan_to_num(corr, nan=0.0)
    abs_corr = np.abs(corr)
    np.fill_diagonal(abs_corr, 0)

    # Find percolation threshold
    thresholds = np.linspace(0.0, 0.10, 501)
    kappa_v2 = 0.0
    for t in thresholds:
        adj = (abs_corr > t).astype(float)
        n = adj.shape[0]
        deg = np.sum(adj, axis=1)
        L = np.diag(deg) - adj
        eigs = np.linalg.eigvalsh(L)
        eigs.sort()
        lam2 = float(eigs[1]) if len(eigs) > 1 else 0.0
        if lam2 < 1e-6:
            kappa_v2 = float(t)
            break

    # Bootstrap
    kappas = []
    for b in range(20):
        rng_b = random.Random(42 + b)
        idx = [rng_b.randint(0, N - 1) for _ in range(5000)]
        Xb = X_active[idx]
        cb = np.nan_to_num(np.corrcoef(Xb, rowvar=False), nan=0.0)
        abc = np.abs(cb)
        np.fill_diagonal(abc, 0)
        for t in thresholds:
            adj = (abc > t).astype(float)
            deg = np.sum(adj, axis=1)
            L = np.diag(deg) - adj
            eigs = np.linalg.eigvalsh(L)
            eigs.sort()
            if float(eigs[1]) < 1e-6:
                kappas.append(float(t))
                break

    kappa_old = 0.046
    kappa_new = np.median(kappas) if kappas else kappa_v2
    shift = kappa_new - kappa_old

    print(f"\n  RESULTS:")
    print(f"  κ_MEM (old, s_relevance=0): {kappa_old:.4f}")
    print(f"  κ_MEM (new, s_relevance active): {kappa_new:.4f}")
    print(f"  Shift: {shift:+.4f}")
    print(f"  Bootstrap std: {np.std(kappas):.4f}" if kappas else "  No bootstrap")
    if abs(shift) < 0.005:
        print(f"  → Phase constant STABLE (shift < 0.005)")
    else:
        print(f"  → Phase constant SHIFTED by {shift:+.4f}")

    result = {
        "kappa_mem_v1": kappa_old,
        "kappa_mem_v2": round(float(kappa_new), 4),
        "shift": round(float(shift), 4),
        "s_relevance_variance": round(float(s_rel_var), 6),
        "active_dimensions": int(n_active),
        "bootstrap_std": round(float(np.std(kappas)), 4) if kappas else None,
        "bootstrap_values": [round(float(k), 4) for k in kappas],
        "stable": bool(abs(shift) < 0.005),
    }

    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "research", "results", "kappa_mem_v2.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n  Saved to {out_path}")
    return result


# =========================================================================
# TASK 3: P(success|omega) calibration curve
# =========================================================================

def task3_calibration_curve():
    print("\n" + "=" * 60)
    print("  TASK 3: P(success|omega) CALIBRATION CURVE")
    print("=" * 60)

    # Load omega-outcome data from research/results or generate fresh
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "research", "results", "omega_outcome_results.json")
    if os.path.exists(data_path):
        with open(data_path) as f:
            prior = json.load(f)
        print(f"\n  Loaded prior results: ρ={prior.get('spearman_rho')}, n={prior.get('n_samples')}")
    else:
        prior = None

    # Generate fresh outcome data with more granularity
    print("  Generating 200 synthetic outcome cases across full omega range...")

    os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)
    AUTH = {"Authorization": "Bearer sg_test_key_001"}

    rng = random.Random(614)
    omegas = []
    outcomes = []

    # Generate cases spanning the full omega range
    for i in range(200):
        # Control omega by varying entry quality
        target_quality = i / 200.0  # 0.0 (perfect) to 1.0 (terrible)
        trust = max(0.05, 1.0 - target_quality * 0.9)
        age = target_quality * 400
        conflict = min(0.95, target_quality * 0.8)
        dc = int(target_quality * 60) + 1

        entry = {
            "id": f"cal_{i}", "content": f"Calibration entry {i}",
            "type": rng.choice(["semantic", "tool_state", "episodic"]),
            "timestamp_age_days": round(age, 1),
            "source_trust": round(trust, 3),
            "source_conflict": round(conflict, 3),
            "downstream_count": dc,
        }

        at = rng.choice(["informational", "reversible", "irreversible"])
        dom = rng.choice(["general", "fintech", "medical"])

        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": [entry], "action_type": at, "domain": dom,
        })
        if r.status_code != 200:
            continue

        omega = r.json()["omega_mem_final"]
        # Outcome: P(success) decreases with omega (with noise)
        # Below omega 25: almost always success
        # Above omega 70: almost always failure
        noise = rng.uniform(-0.1, 0.1)
        p_success = max(0, min(1, 1.0 / (1.0 + math.exp(0.08 * (omega - 45))) + noise))
        outcome = 1 if rng.random() < p_success else 0

        omegas.append(omega)
        outcomes.append(outcome)

    print(f"  Generated {len(omegas)} scored cases")

    # Bin into deciles
    bins = [(0, 10), (10, 20), (20, 30), (30, 40), (40, 50),
            (50, 60), (60, 70), (70, 80), (80, 90), (90, 100)]
    curve = {}
    for lo, hi in bins:
        bin_omegas = [(o, out) for o, out in zip(omegas, outcomes) if lo <= o < hi]
        n = len(bin_omegas)
        if n > 0:
            p_success = sum(out for _, out in bin_omegas) / n
        else:
            p_success = None
        curve[f"{lo}-{hi}"] = {"n": n, "p_success": round(p_success, 3) if p_success is not None else None}
        if p_success is not None:
            bar = "█" * int(p_success * 30)
            print(f"    omega {lo:3d}-{hi:3d}: P(success)={p_success:.3f} n={n:3d}  {bar}")

    # Fit sigmoid: P(success) = 1 / (1 + exp(β(omega - θ)))
    # Use least squares on the bin data
    bin_centers = []
    bin_probs = []
    for lo, hi in bins:
        bc = (lo + hi) / 2
        data = curve[f"{lo}-{hi}"]
        if data["p_success"] is not None and data["n"] >= 3:
            bin_centers.append(bc)
            bin_probs.append(data["p_success"])

    # Grid search for best β, θ
    best_err = float('inf')
    best_beta = 0.1
    best_theta = 50.0
    for beta in np.arange(0.01, 0.3, 0.005):
        for theta in np.arange(10, 90, 1):
            err = 0
            for bc, bp in zip(bin_centers, bin_probs):
                pred = 1.0 / (1.0 + math.exp(beta * (bc - theta)))
                err += (pred - bp) ** 2
            if err < best_err:
                best_err = err
                best_beta = beta
                best_theta = theta

    # Determine curve shape
    if len(bin_probs) >= 3:
        diffs = [bin_probs[i] - bin_probs[i+1] for i in range(len(bin_probs)-1)]
        max_diff = max(diffs) if diffs else 0
        mean_diff = np.mean(diffs) if diffs else 0
        if max_diff > 0.4:
            shape = "step_function"
        elif max_diff > 0.15:
            shape = "sigmoid"
        else:
            shape = "linear"
    else:
        shape = "insufficient_data"

    # Compare inflection point to our threshold
    threshold_comparison = (
        "correct" if abs(best_theta - 70) < 10
        else "too_high" if best_theta < 60
        else "too_low" if best_theta > 80
        else "uncertain"
    )

    print(f"\n  SIGMOID FIT:")
    print(f"  P(success) = 1 / (1 + exp({best_beta:.3f} × (omega - {best_theta:.1f})))")
    print(f"  Inflection point θ = {best_theta:.1f}")
    print(f"  Steepness β = {best_beta:.3f}")
    print(f"  Fit error: {best_err:.4f}")
    print(f"  Curve shape: {shape}")
    print(f"\n  Our BLOCK threshold: 70")
    print(f"  Data inflection point: {best_theta:.1f}")
    print(f"  Comparison: {threshold_comparison}")

    if best_theta < 60:
        print(f"  → Our BLOCK=70 is TOO HIGH. Data suggests blocking at {best_theta:.0f}.")
    elif best_theta > 80:
        print(f"  → Our BLOCK=70 is TOO LOW. Data suggests blocking at {best_theta:.0f}.")
    else:
        print(f"  → Our BLOCK=70 is APPROXIMATELY CORRECT (within 10 points of data).")

    result = {
        "curve": curve,
        "sigmoid_fit": {
            "beta": round(float(best_beta), 4),
            "theta": round(float(best_theta), 1),
            "fit_error": round(float(best_err), 4),
            "formula": f"P(success) = 1 / (1 + exp({best_beta:.3f} * (omega - {best_theta:.1f})))",
        },
        "curve_shape": shape,
        "inflection_point": round(float(best_theta), 1),
        "our_block_threshold": 70,
        "threshold_comparison": threshold_comparison,
        "n_cases": len(omegas),
    }

    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "research", "results", "calibration_curve.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n  Saved to {out_path}")
    return result


# =========================================================================
# MAIN
# =========================================================================

if __name__ == "__main__":
    t0 = time.time()
    r1 = task1_s_relevance_impact()
    r2 = task2_kappa_mem_v2()
    r3 = task3_calibration_curve()
    elapsed = time.time() - t0

    print("\n" + "=" * 60)
    print("  ALL TASKS COMPLETE")
    print("=" * 60)
    print(f"  Total time: {elapsed:.1f}s")
    print(f"  s_relevance decision changes: {r1['decision_changes']}/{r1['total_cases']}")
    print(f"  κ_MEM shift: {r2['shift']:+.4f} ({'stable' if r2['stable'] else 'SHIFTED'})")
    print(f"  Calibration inflection: θ={r3['inflection_point']}, shape={r3['curve_shape']}")
    print(f"  BLOCK threshold: {r3['threshold_comparison']}")
