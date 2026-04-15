#!/usr/bin/env python3
"""
Thermodynamic shape analysis: Does heat distribution deform the scoring space?
"""
import sys, os, math, json, random, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"

from fastapi.testclient import TestClient
from api.main import app, _load_benchmark_corpus
from scoring_engine import compute, MemoryEntry

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

MEMORY_TYPES = ["tool_state", "shared_workflow", "episodic", "preference", "semantic", "policy", "identity"]
DOMAINS = ["general", "customer_support", "coding", "legal", "fintech", "medical"]
PC_NAMES = ["PC1_Risk", "PC2_Decay", "PC3_Trust", "PC4_Corruption", "PC5_Belief"]
COMPONENT_KEYS = ["s_freshness", "s_drift", "s_provenance", "s_propagation",
                  "r_recall", "r_encode", "s_interference", "s_recovery",
                  "r_belief", "s_relevance", "omega", "assurance"]


def collect_corpus_vectors():
    cases = _load_benchmark_corpus()
    vectors = []
    for i, case in enumerate(cases):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": case["memory_state"],
            "action_type": case.get("action_type", "reversible"),
            "domain": case.get("domain", "general"), "dry_run": True,
        })
        if r.status_code == 200:
            pf = r.json()
            cb = pf.get("component_breakdown", {})
            vec = [cb.get(k, 0) / 100.0 for k in COMPONENT_KEYS[:10]]
            vec.append(pf.get("omega_mem_final", 0) / 100.0)
            vec.append(pf.get("assurance_score", 0) / 100.0)
            vectors.append(vec)
    return np.array(vectors)


def simulate_agents(n_agents=10, n_steps=30):
    agents = {}
    for idx in range(n_agents):
        rng = random.Random(idx * 77)
        aid = f"thermo-agent-{idx:03d}"
        n_entries = rng.randint(3, 8)
        base = [{"content": f"Mem {j} " + rng.choice(["a","b","c"]) * 3,
                 "type": rng.choice(MEMORY_TYPES), "base_age": rng.uniform(0.5, 10),
                 "trust": rng.uniform(0.5, 0.95), "conflict": rng.uniform(0.02, 0.3),
                 "downstream": rng.randint(1, 15), "belief": rng.uniform(0.5, 0.95)}
                for j in range(n_entries)]
        heal_interval = rng.randint(10, 25)
        vectors = []
        for step in range(n_steps):
            entries = []
            for e in base:
                age = e["base_age"] + step * 0.7
                trust, conflict = e["trust"], e["conflict"]
                if step > 0 and step % heal_interval == 0:
                    age = 0.1; trust = min(0.99, trust + 0.1); conflict = max(0.02, conflict - 0.05)
                if rng.random() < 0.05:
                    conflict = min(0.9, conflict + 0.3)
                entries.append({"id": f"e_{idx}_{step}_{len(entries)}",
                                "content": e["content"], "type": e["type"],
                                "timestamp_age_days": round(age, 1),
                                "source_trust": round(trust, 3),
                                "source_conflict": round(conflict, 3),
                                "downstream_count": e["downstream"]})
            r = client.post("/v1/preflight", headers=AUTH, json={
                "memory_state": entries, "action_type": "reversible",
                "domain": rng.choice(DOMAINS), "agent_id": aid, "dry_run": True,
            })
            if r.status_code == 200:
                pf = r.json()
                cb = pf.get("component_breakdown", {})
                vec = [cb.get(k, 0) / 100.0 for k in COMPONENT_KEYS[:10]]
                vec.append(pf.get("omega_mem_final", 0) / 100.0)
                vec.append(pf.get("assurance_score", 0) / 100.0)
                vectors.append(vec)
        agents[aid] = np.array(vectors)
    return agents


def get_pca(X):
    var = np.var(X, axis=0)
    active = var > 1e-8
    Xa = X[:, active]
    Xs = (Xa - np.mean(Xa, axis=0)) / (np.std(Xa, axis=0) + 1e-10)
    cov = np.cov(Xs, rowvar=False)
    eig_vals, eig_vecs = np.linalg.eigh(cov)
    idx = np.argsort(eig_vals)[::-1]
    return eig_vals[idx], eig_vecs[:, idx], Xs, active


# =========================================================================
# TASK 1: Temperature map
# =========================================================================

def task1_temperature_map(eig_vals):
    print("=" * 60)
    print("  TASK 1: TEMPERATURE MAP")
    print("=" * 60)

    top5 = eig_vals[:5]
    mean_eig = np.mean(top5)
    total = np.sum(top5)
    equi_expected = total / 5.0

    temp_map = {}
    for i, (name, ev) in enumerate(zip(PC_NAMES, top5)):
        pct_var = ev / total * 100
        equi_dev = (ev - equi_expected) / equi_expected * 100
        T_i = ev / mean_eig
        temp_map[name] = {
            "eigenvalue": round(float(ev), 4),
            "pct_variance": round(float(pct_var), 1),
            "equipartition_deviation_pct": round(float(equi_dev), 1),
            "temperature_T_i": round(float(T_i), 3),
        }
        hot = "HOT" if T_i > 1.2 else "COLD" if T_i < 0.8 else "warm"
        print(f"    {name:16s}: λ={ev:.4f}, T={T_i:.3f} ({pct_var:.1f}% var, {equi_dev:+.0f}% from equi) [{hot}]")

    print(f"\n    Mean eigenvalue: {mean_eig:.4f}")
    print(f"    Equipartition: {equi_expected:.4f} per axis")
    print(f"    Max/Min temperature ratio: {max(top5)/min(top5):.2f}")
    return temp_map


# =========================================================================
# TASK 2: Onsager coupling matrix
# =========================================================================

def task2_onsager(X_proj):
    print("\n" + "=" * 60)
    print("  TASK 2: ONSAGER COUPLING MATRIX")
    print("=" * 60)

    # Cross-correlation between PC scores
    corr = np.corrcoef(X_proj[:, :5], rowvar=False)
    corr = np.nan_to_num(corr)

    print(f"\n    Cross-correlation (Onsager matrix):")
    print(f"    {'':16s}", end="")
    for name in PC_NAMES:
        print(f"  {name[:5]:>6s}", end="")
    print()
    for i, name in enumerate(PC_NAMES):
        print(f"    {name:16s}", end="")
        for j in range(5):
            val = corr[i][j]
            print(f"  {val:+.3f}", end="")
        print()

    # Test symmetry: |L_ij - L_ji| for off-diagonal
    asymmetry = []
    for i in range(5):
        for j in range(i+1, 5):
            asym = abs(corr[i][j] - corr[j][i])
            asymmetry.append(asym)

    max_asym = max(asymmetry) if asymmetry else 0
    mean_asym = np.mean(asymmetry) if asymmetry else 0
    symmetric = max_asym < 0.01

    print(f"\n    Symmetry test (Onsager reciprocity):")
    print(f"    Max |L_ij - L_ji|: {max_asym:.6f}")
    print(f"    Mean asymmetry: {mean_asym:.6f}")
    print(f"    Symmetric: {'YES' if symmetric else 'NO'}")
    if symmetric:
        print(f"    → Onsager reciprocity HOLDS: system is near equilibrium locally")
    else:
        print(f"    → Onsager reciprocity VIOLATED: far from equilibrium")

    # Find strongest off-diagonal couplings
    couplings = []
    for i in range(5):
        for j in range(i+1, 5):
            couplings.append((PC_NAMES[i], PC_NAMES[j], float(corr[i][j])))
    couplings.sort(key=lambda x: abs(x[2]), reverse=True)

    print(f"\n    Strongest couplings:")
    for a, b, c in couplings[:3]:
        direction = "positive (energy exchange)" if c > 0 else "negative (anti-correlated)"
        print(f"    {a} ↔ {b}: {c:+.3f} ({direction})")

    return {
        "matrix": [[round(float(corr[i][j]), 4) for j in range(5)] for i in range(5)],
        "symmetric": symmetric,
        "max_asymmetry": round(float(max_asym), 6),
        "strongest_coupling": {"axes": [couplings[0][0], couplings[0][1]], "value": round(couplings[0][2], 4)} if couplings else None,
    }


# =========================================================================
# TASK 3: Dissipative structure detection
# =========================================================================

def task3_dissipative(agents, eig_vecs, active_mask):
    print("\n" + "=" * 60)
    print("  TASK 3: DISSIPATIVE STRUCTURE DETECTION")
    print("=" * 60)

    # For each agent trajectory, compute entropy production per axis
    axis_sigma = {name: [] for name in PC_NAMES}

    for aid, traj in agents.items():
        if len(traj) < 5:
            continue
        # Standardize and project
        var = np.var(traj, axis=0)
        act = var > 1e-8
        # Use only columns that match the active_mask
        common = min(traj.shape[1], len(active_mask))
        traj_a = traj[:, :common][:, active_mask[:common]]
        if traj_a.shape[1] < eig_vecs.shape[0]:
            continue
        traj_s = (traj_a - np.mean(traj_a, axis=0)) / (np.std(traj_a, axis=0) + 1e-10)
        traj_proj = traj_s @ eig_vecs[:traj_s.shape[1], :5]

        for ax in range(5):
            scores = traj_proj[:, ax]
            deltas = np.abs(np.diff(scores))
            sigma = float(np.mean(deltas)) if len(deltas) > 0 else 0
            axis_sigma[PC_NAMES[ax]].append(sigma)

    print(f"\n    Entropy production rate σ per axis:")
    sources = []
    sinks = []
    for name in PC_NAMES:
        vals = axis_sigma[name]
        if vals:
            mean_s = np.mean(vals)
            std_s = np.std(vals)
            print(f"    {name:16s}: σ = {mean_s:.4f} ± {std_s:.4f}", end="")
            if mean_s > np.mean([np.mean(axis_sigma[n]) for n in PC_NAMES if axis_sigma[n]]) * 1.2:
                print(f"  [SOURCE — high entropy production]")
                sources.append(name)
            elif mean_s < np.mean([np.mean(axis_sigma[n]) for n in PC_NAMES if axis_sigma[n]]) * 0.8:
                print(f"  [SINK — low entropy production]")
                sinks.append(name)
            else:
                print(f"  [neutral]")

    stable = len(sources) > 0 and len(sinks) > 0
    print(f"\n    Entropy sources: {sources if sources else 'none'}")
    print(f"    Entropy sinks:   {sinks if sinks else 'none'}")
    print(f"    Stable dissipative pattern: {'YES' if stable else 'NO'}")
    if stable:
        print(f"    → Prigogine dissipative structure detected: energy flows from {sources} to {sinks}")

    return {
        "entropy_production_per_axis": {name: round(float(np.mean(axis_sigma[name])), 4) if axis_sigma[name] else 0 for name in PC_NAMES},
        "sources": sources,
        "sinks": sinks,
        "dissipative_structure": stable,
    }


# =========================================================================
# TASK 4: Phase space trajectory classification
# =========================================================================

def task4_trajectories(agents, eig_vecs, active_mask):
    print("\n" + "=" * 60)
    print("  TASK 4: PHASE SPACE TRAJECTORIES")
    print("=" * 60)

    trajectory_types = {}

    for aid, traj in agents.items():
        if len(traj) < 10:
            trajectory_types[aid] = {"type": "insufficient_data", "n_steps": len(traj)}
            continue

        common = min(traj.shape[1], len(active_mask))
        traj_a = traj[:, :common][:, active_mask[:common]]
        if traj_a.shape[1] < eig_vecs.shape[0]:
            trajectory_types[aid] = {"type": "dimension_mismatch"}
            continue
        traj_s = (traj_a - np.mean(traj_a, axis=0)) / (np.std(traj_a, axis=0) + 1e-10)
        traj_proj = traj_s @ eig_vecs[:traj_s.shape[1], :5]

        pc1 = traj_proj[:, 0]
        pc2 = traj_proj[:, 1]

        # Test 1: Does it converge? (last 5 points variance < first 5)
        var_first = np.var(pc1[:5]) + np.var(pc2[:5])
        var_last = np.var(pc1[-5:]) + np.var(pc2[-5:])
        converging = var_last < var_first * 0.3

        # Test 2: Does it orbit? (autocorrelation has periodic peak)
        signal = pc1 - np.mean(pc1)
        if np.std(signal) > 1e-6:
            autocorr = np.correlate(signal, signal, mode='full')
            autocorr = autocorr[len(autocorr)//2:]  # Positive lags only
            autocorr = autocorr / (autocorr[0] + 1e-10)
            # Find first peak after lag 2
            peaks = []
            for lag in range(3, len(autocorr) - 1):
                if autocorr[lag] > autocorr[lag-1] and autocorr[lag] > autocorr[lag+1] and autocorr[lag] > 0.3:
                    peaks.append(lag)
                    break
            periodic = len(peaks) > 0
            period = peaks[0] if peaks else None
        else:
            periodic = False
            period = None

        # Test 3: Area coverage (how much of PC1-PC2 box is filled)
        if np.std(pc1) > 1e-6 and np.std(pc2) > 1e-6:
            pc1_n = (pc1 - np.min(pc1)) / (np.max(pc1) - np.min(pc1) + 1e-10)
            pc2_n = (pc2 - np.min(pc2)) / (np.max(pc2) - np.min(pc2) + 1e-10)
            grid = np.zeros((10, 10))
            for p1, p2 in zip(pc1_n, pc2_n):
                gi = min(9, int(p1 * 10))
                gj = min(9, int(p2 * 10))
                grid[gi][gj] = 1
            fill_ratio = np.sum(grid) / 100
        else:
            fill_ratio = 0

        # Classify
        if converging:
            ttype = "fixed_point"
        elif periodic:
            ttype = "limit_cycle"
        elif fill_ratio > 0.3:
            ttype = "quasiperiodic"
        else:
            ttype = "transient"

        trajectory_types[aid] = {
            "type": ttype,
            "converging": bool(converging),
            "periodic": bool(periodic),
            "period": int(period) if period else None,
            "area_fill_ratio": round(float(fill_ratio), 3),
            "n_steps": len(traj),
        }
        print(f"    {aid}: {ttype} (fill={fill_ratio:.2f}, periodic={periodic}, converging={converging})")

    # Summary
    type_counts = {}
    for t in trajectory_types.values():
        tt = t.get("type", "unknown")
        type_counts[tt] = type_counts.get(tt, 0) + 1

    print(f"\n    Trajectory types: {type_counts}")
    dominant = max(type_counts, key=type_counts.get) if type_counts else "none"
    print(f"    Dominant: {dominant}")

    return {"trajectories": trajectory_types, "type_counts": type_counts, "dominant_type": dominant}


# =========================================================================
# MAIN
# =========================================================================

def main():
    t0 = time.time()
    print("Collecting corpus vectors + simulating agents...\n")

    X = collect_corpus_vectors()
    print(f"Corpus vectors: {X.shape}")

    agents = simulate_agents(n_agents=10, n_steps=30)
    print(f"Simulated {len(agents)} agents\n")

    eig_vals, eig_vecs, X_std, active = get_pca(X)

    r1 = task1_temperature_map(eig_vals)
    X_proj = X_std @ eig_vecs[:, :5]
    r2 = task2_onsager(X_proj)
    r3 = task3_dissipative(agents, eig_vecs, active)
    r4 = task4_trajectories(agents, eig_vecs, active)

    result = {
        "temperature_map": r1,
        "onsager_coupling": r2,
        "dissipative_structure": r3,
        "phase_trajectories": r4,
        "elapsed_seconds": round(time.time() - t0, 1),
    }

    def _jd(x):
        if isinstance(x, (np.floating,)): return float(x)
        if isinstance(x, (np.integer,)): return int(x)
        if isinstance(x, (np.bool_,)): return bool(x)
        return str(x)

    out = os.path.join(os.path.dirname(os.path.dirname(__file__)), "research", "results", "thermodynamic_shape.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=2, default=_jd)

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Time: {time.time()-t0:.1f}s")
    hot = [k for k, v in r1.items() if v["temperature_T_i"] > 1.2]
    cold = [k for k, v in r1.items() if v["temperature_T_i"] < 0.8]
    print(f"  Hot axes: {hot}")
    print(f"  Cold axes: {cold}")
    print(f"  Onsager symmetric: {r2['symmetric']}")
    print(f"  Dissipative structure: {r3['dissipative_structure']}")
    print(f"  Dominant trajectory: {r4['dominant_type']}")
    print(f"  Saved to {out}")


if __name__ == "__main__":
    main()
