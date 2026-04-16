#!/usr/bin/env python3
"""
Five research analysis tasks (#604-610). All use existing data.
"""
import sys, os, math, json, random, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from fastapi.testclient import TestClient
from api.main import app, _load_benchmark_corpus, _outcome_set
from scoring_engine import compute, MemoryEntry

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

MEMORY_TYPES = ["tool_state", "shared_workflow", "episodic", "preference", "semantic", "policy", "identity"]
DOMAINS = ["general", "customer_support", "coding", "legal", "fintech", "medical"]


def _seed_agent_trajectories():
    """Generate multi-call trajectories for 10 agents."""
    agents = {}
    for agent_idx in range(10):
        rng = random.Random(agent_idx * 100)
        aid = f"research-agent-{agent_idx:03d}"
        agents[aid] = []
        n_entries = rng.randint(3, 8)
        base_entries = []
        for j in range(n_entries):
            base_entries.append({
                "content": f"Memory {j} " + rng.choice(["alpha", "beta", "gamma"]) * 3,
                "type": rng.choice(MEMORY_TYPES),
                "base_age": rng.uniform(0.5, 10),
                "trust": rng.uniform(0.5, 0.95),
                "conflict": rng.uniform(0.02, 0.3),
                "downstream": rng.randint(1, 15),
                "belief": rng.uniform(0.5, 0.95),
            })

        heal_interval = rng.randint(10, 25)
        for step in range(25):
            entries = []
            for e in base_entries:
                age = e["base_age"] + step * 0.7
                trust = e["trust"]
                conflict = e["conflict"]
                if step > 0 and step % heal_interval == 0:
                    age = 0.1
                    trust = min(0.99, trust + 0.1)
                    conflict = max(0.02, conflict - 0.05)
                if rng.random() < 0.05:
                    conflict = min(0.9, conflict + 0.3)
                entries.append({
                    "id": f"e_{aid}_{step}_{len(entries)}",
                    "content": e["content"], "type": e["type"],
                    "timestamp_age_days": round(age, 1),
                    "source_trust": round(trust, 3),
                    "source_conflict": round(conflict, 3),
                    "downstream_count": e["downstream"],
                })

            r = client.post("/v1/preflight", headers=AUTH, json={
                "memory_state": entries, "action_type": "reversible",
                "domain": rng.choice(DOMAINS), "agent_id": aid, "dry_run": True,
            })
            if r.status_code == 200:
                agents[aid].append(r.json())

    return agents


# =========================================================================
# TASK 1: Conservation law test
# =========================================================================

def task1_conservation(agents):
    print("=" * 60)
    print("  TASK 1: CONSERVATION LAW TEST")
    print("=" * 60)

    agent_sums = {}
    for aid, calls in agents.items():
        sums = []
        for pf in calls:
            cb = pf.get("component_breakdown", {})
            if not cb:
                continue
            total = sum(v for v in cb.values() if isinstance(v, (int, float)))
            sums.append(total)
        if len(sums) >= 5:
            agent_sums[aid] = {"mean": np.mean(sums), "std": np.std(sums), "n": len(sums),
                                "min": min(sums), "max": max(sums)}

    all_stds = [v["std"] for v in agent_sums.values()]
    all_means = [v["mean"] for v in agent_sums.values()]
    conserved_count = sum(1 for s in all_stds if s < 5.0)

    print(f"\n  Agents analyzed: {len(agent_sums)}")
    for aid, stats in sorted(agent_sums.items()):
        conserved = "CONSERVED" if stats["std"] < 5.0 else "varying"
        print(f"    {aid}: mean={stats['mean']:.1f}, std={stats['std']:.1f}, range=[{stats['min']:.1f}, {stats['max']:.1f}] [{conserved}]")

    overall_mean = np.mean(all_means) if all_means else 0
    overall_std = np.mean(all_stds) if all_stds else 0
    conservation = conserved_count / max(len(agent_sums), 1) > 0.5

    if conservation:
        interp = f"Conservation law DETECTED: {conserved_count}/{len(agent_sums)} agents have component_sum std < 5.0. The total risk is approximately conserved — it moves between components rather than appearing or disappearing."
    else:
        interp = f"No conservation law: {conserved_count}/{len(agent_sums)} agents have stable sums. Component_sum varies significantly — total risk is not conserved."

    print(f"\n  {interp}")

    result = {
        "conservation_detected": conservation,
        "mean_component_sum": round(float(overall_mean), 1),
        "std_component_sum": round(float(overall_std), 1),
        "agents_analyzed": len(agent_sums),
        "conserved_agents": conserved_count,
        "interpretation": interp,
    }
    _save("conservation_law.json", result)
    return result


# =========================================================================
# TASK 2: Healing loop natural frequency
# =========================================================================

def task2_natural_frequency(agents):
    print("\n" + "=" * 60)
    print("  TASK 2: HEALING LOOP NATURAL FREQUENCY")
    print("=" * 60)

    agent_periods = []

    for aid, calls in agents.items():
        omegas = [pf.get("omega_mem_final", 0) for pf in calls]
        if len(omegas) < 10:
            continue

        # FFT
        signal = np.array(omegas) - np.mean(omegas)
        window = np.hanning(len(signal))
        fft_vals = np.fft.rfft(signal * window)
        power = np.abs(fft_vals) ** 2
        freqs = np.fft.rfftfreq(len(signal))

        # Find peak (skip DC)
        if len(power) > 2:
            peak_idx = np.argmax(power[1:]) + 1
            peak_freq = freqs[peak_idx]
            if peak_freq > 0:
                period_calls = 1.0 / peak_freq
                period_days = period_calls  # Assuming ~1 call/day
                agent_periods.append({"agent_id": aid, "period_calls": round(period_calls, 1),
                                       "period_days": round(period_days, 1), "peak_power": round(float(power[peak_idx]), 1)})
                print(f"    {aid}: T={period_calls:.1f} calls ({period_days:.1f} days)")

    if agent_periods:
        periods = [p["period_days"] for p in agent_periods]
        fleet_median = np.median(periods)
        fleet_mean = np.mean(periods)
        matches_weibull = 10 <= fleet_median <= 20

        print(f"\n  Fleet median period: {fleet_median:.1f} days")
        print(f"  Fleet mean period:   {fleet_mean:.1f} days")
        print(f"  Weibull episodic half-life: ~14 days")
        print(f"  Match: {'YES' if matches_weibull else 'NO'}")
    else:
        fleet_median = 0
        fleet_mean = 0
        matches_weibull = False

    result = {
        "agents_analyzed": len(agent_periods),
        "agent_periods": agent_periods,
        "fleet_median_period_days": round(float(fleet_median), 1),
        "fleet_mean_period_days": round(float(fleet_mean), 1),
        "matches_weibull_episodic": bool(matches_weibull),
        "weibull_episodic_halflife": 14,
    }
    _save("natural_frequency.json", result)
    return result


# =========================================================================
# TASK 3: Detection layer temporal ordering
# =========================================================================

def task3_detection_ordering():
    print("\n" + "=" * 60)
    print("  TASK 3: DETECTION LAYER TEMPORAL ORDERING")
    print("=" * 60)

    cases = _load_benchmark_corpus()
    print(f"\n  Running {len(cases)} corpus cases for detection ordering...")

    layers = ["timestamp_integrity", "identity_drift", "consensus_collapse", "provenance_chain_integrity"]
    layer_positions = {l: [] for l in layers}
    total_compound = 0

    for i, case in enumerate(cases):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": case["memory_state"],
            "action_type": case.get("action_type", "reversible"),
            "domain": case.get("domain", "general"), "dry_run": True,
        })
        if r.status_code != 200:
            continue
        pf = r.json()

        fired = []
        for layer in layers:
            val = pf.get(layer, "CLEAN")
            if val in ("MANIPULATED", "SUSPICIOUS"):
                fired.append((layer, 0 if val == "MANIPULATED" else 1))  # MANIPULATED fires "first"

        if len(fired) >= 2:
            total_compound += 1
            # Sort by severity (MANIPULATED before SUSPICIOUS)
            fired.sort(key=lambda x: x[1])
            for pos, (layer, _) in enumerate(fired):
                layer_positions[layer].append(pos + 1)

        if (i + 1) % 100 == 0:
            print(f"    {i+1}/{len(cases)}...")

    ordering = []
    for layer in layers:
        positions = layer_positions[layer]
        if positions:
            avg_pos = np.mean(positions)
            fires_first = sum(1 for p in positions if p == 1) / max(len(positions), 1) * 100
            ordering.append({"layer": layer, "avg_position": round(float(avg_pos), 2),
                             "fires_first_pct": round(float(fires_first), 1), "times_fired": len(positions)})

    ordering.sort(key=lambda x: x["avg_position"])
    canary = ordering[0]["layer"] if ordering else "none"

    print(f"\n  Compound attacks analyzed: {total_compound}")
    for o in ordering:
        print(f"    {o['layer']:35s}: avg_pos={o['avg_position']:.2f}, fires_first={o['fires_first_pct']:.0f}%")
    print(f"  Canary layer: {canary}")

    result = {
        "compound_attacks_analyzed": total_compound,
        "firing_order": ordering,
        "canary_layer": canary,
    }
    _save("detection_ordering.json", result)
    return result


# =========================================================================
# TASK 4: Monoculture risk vs detection rate
# =========================================================================

def task4_monoculture_detection():
    print("\n" + "=" * 60)
    print("  TASK 4: MONOCULTURE RISK VS DETECTION RATE")
    print("=" * 60)

    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "corpus", "round9_federated_poisoning.json")) as f:
        cases = json.load(f)

    print(f"\n  Running {len(cases)} Round 9 cases...")

    groups = {"LOW": {"n": 0, "detected": 0, "scores": []},
              "MEDIUM": {"n": 0, "detected": 0, "scores": []},
              "HIGH": {"n": 0, "detected": 0, "scores": []}}

    for case in cases:
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": case["memory_state"],
            "action_type": "irreversible", "domain": "fintech", "dry_run": True,
        })
        if r.status_code != 200:
            continue
        pf = r.json()
        mono_level = pf.get("monoculture_risk_level", "LOW")
        mono_score = pf.get("monoculture_risk_score", 0)
        action = pf.get("recommended_action", "USE_MEMORY")
        expected = case.get("expected_decision", "BLOCK")

        detected = action in ("BLOCK", "WARN", "ASK_USER") if expected in ("BLOCK", "WARN") else True

        if mono_level in groups:
            groups[mono_level]["n"] += 1
            groups[mono_level]["scores"].append(mono_score)
            if detected:
                groups[mono_level]["detected"] += 1

    for level, g in groups.items():
        g["detection_rate"] = round(g["detected"] / max(g["n"], 1), 4)
        g["mean_score"] = round(np.mean(g["scores"]), 3) if g["scores"] else 0
        del g["scores"]  # Don't save raw scores
        print(f"    {level}: n={g['n']}, detection_rate={g['detection_rate']:.3f}")

    # Correlation: do higher monoculture levels have lower detection?
    level_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    if groups["LOW"]["n"] > 0 and groups["HIGH"]["n"] > 0:
        corr = groups["HIGH"]["detection_rate"] - groups["LOW"]["detection_rate"]
        if corr < -0.05:
            interp = "HIGH monoculture cases have LOWER detection rates — diverse ecosystems are harder to attack."
        elif corr > 0.05:
            interp = "HIGH monoculture cases have HIGHER detection rates — monocultures are easier to detect (paradox)."
        else:
            interp = "No significant correlation between monoculture risk and detection rate."
    else:
        corr = 0
        interp = "Insufficient data for correlation."

    print(f"\n  Correlation: {corr:+.3f}")
    print(f"  {interp}")

    result = {**groups, "correlation": round(float(corr), 4), "interpretation": interp}
    _save("monoculture_detection.json", result)
    return result


# =========================================================================
# TASK 5: block_explanation archetypes
# =========================================================================

def task5_block_archetypes(agents):
    print("\n" + "=" * 60)
    print("  TASK 5: BLOCK_EXPLANATION ARCHETYPES")
    print("=" * 60)

    # Collect explanations from agent trajectories + corpus
    explanations = []
    for aid, calls in agents.items():
        for pf in calls:
            exp = pf.get("block_explanation")
            if exp and isinstance(exp, str):
                explanations.append(exp)

    # Also run corpus for more explanations
    cases = _load_benchmark_corpus()
    for case in cases[:200]:
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": case["memory_state"],
            "action_type": case.get("action_type", "reversible"),
            "domain": case.get("domain", "general"), "dry_run": True,
        })
        if r.status_code == 200:
            exp = r.json().get("block_explanation")
            if exp:
                explanations.append(exp)

    print(f"\n  Collected {len(explanations)} explanations")

    if not explanations:
        result = {"archetypes": [], "total_explanations": 0, "coverage": 0}
        _save("block_archetypes.json", result)
        return result

    # Tokenize
    stop = {"this", "that", "with", "have", "from", "the", "and", "for", "are", "not", "entry", "fix"}
    tokens = [set(w.lower() for w in e.split() if len(w) >= 4 and w.lower() not in stop) for e in explanations]

    # Cluster by Jaccard > 0.4
    n = len(explanations)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[a] = b

    for i in range(n):
        for j in range(i + 1, n):
            if tokens[i] and tokens[j]:
                inter = len(tokens[i] & tokens[j])
                uni = len(tokens[i] | tokens[j])
                if uni > 0 and inter / uni > 0.4:
                    union(i, j)

    # Group clusters
    clusters = {}
    for i in range(n):
        root = find(i)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(i)

    # Sort by size, pick representative (shortest explanation in cluster)
    sorted_clusters = sorted(clusters.values(), key=len, reverse=True)
    archetypes = []
    for cluster in sorted_clusters[:10]:
        rep_idx = min(cluster, key=lambda i: len(explanations[i]))
        archetypes.append({
            "archetype_id": len(archetypes) + 1,
            "representative": explanations[rep_idx],
            "size": len(cluster),
            "pct": round(len(cluster) / n * 100, 1),
        })

    coverage = sum(a["size"] for a in archetypes) / max(n, 1)

    print(f"\n  Archetypes found: {len(archetypes)}")
    for a in archetypes[:5]:
        print(f"    #{a['archetype_id']} ({a['size']} cases, {a['pct']}%): {a['representative'][:80]}")
    print(f"\n  Coverage (top {len(archetypes)} archetypes): {coverage*100:.1f}%")

    result = {"archetypes": archetypes, "total_explanations": n, "coverage": round(float(coverage), 3)}
    _save("block_archetypes.json", result)
    return result


# =========================================================================
# Helpers
# =========================================================================

def _save(filename, data):
    out = os.path.join(os.path.dirname(os.path.dirname(__file__)), "research", "results", filename)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    def _json_default(x):
        if isinstance(x, (np.floating,)):
            return float(x)
        if isinstance(x, (np.integer,)):
            return int(x)
        if isinstance(x, (np.bool_,)):
            return bool(x)
        if isinstance(x, np.ndarray):
            return x.tolist()
        return str(x)
    with open(out, "w") as f:
        json.dump(data, f, indent=2, default=_json_default)
    print(f"  Saved to {out}")


# =========================================================================
# MAIN
# =========================================================================

if __name__ == "__main__":
    t0 = time.time()
    print("Seeding agent trajectories (10 agents × 25 calls)...\n")
    agents = _seed_agent_trajectories()
    print(f"Seeded {len(agents)} agents, {sum(len(v) for v in agents.values())} total calls\n")

    r1 = task1_conservation(agents)
    r2 = task2_natural_frequency(agents)
    r3 = task3_detection_ordering()
    r4 = task4_monoculture_detection()
    r5 = task5_block_archetypes(agents)

    print("\n" + "=" * 60)
    print("  ALL TASKS COMPLETE")
    print("=" * 60)
    print(f"  Time: {time.time()-t0:.1f}s")
    print(f"  Conservation: {'DETECTED' if r1['conservation_detected'] else 'NOT detected'}")
    print(f"  Natural frequency: {r2['fleet_median_period_days']} days (Weibull match: {r2['matches_weibull_episodic']})")
    print(f"  Canary layer: {r3['canary_layer']}")
    print(f"  Monoculture correlation: {r4['correlation']:+.3f}")
    print(f"  Block archetypes: {len(r5['archetypes'])} found, {r5['coverage']*100:.0f}% coverage")
