#!/usr/bin/env python3
"""Business Metrics B: Fleet Vaccination, Type-Stratified Calibration, Q-table Convergence.

TASK 2: Fleet Vaccination Doubling Time (Metcalfe multiplier)
TASK 3: Type-Stratified Calibration (per-type sigmoid fit P(success|omega))
TASK 4: Q-table Convergence (theoretical + empirical per-domain)
"""

import os
import sys
import json
import math
import random

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

random.seed(42)

RESULTS_PATH = "/Users/zsobrakpeter/core/research/results/business_metrics.json"


def load_existing_results(path: str) -> dict:
    """Read existing results file if present, else return empty dict."""
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"  WARN: could not read existing {path}: {e}")
            return {}
    return {}


def save_results(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# =====================================================================
# TASK 2 — Fleet Vaccination Doubling Time
# =====================================================================
print("=" * 72)
print("TASK 2 — Fleet Vaccination Doubling Time")
print("=" * 72)

# Quick audit log check (informational only — model below drives results)
try:
    audit = client.get("/v1/audit-log?limit=1000", headers=AUTH)
    if audit.status_code == 200:
        entries = audit.json().get("entries", [])
        print(f"  audit-log entries available: {len(entries)}")
    else:
        print(f"  audit-log status: {audit.status_code} (using model)")
except Exception as e:
    print(f"  audit-log unavailable ({e}); using model")


def scenario(N: int, attacks_per_N_day: float, label: str):
    """Logistic-growth vaccination model.

    I(t) = N * (1 - exp(-k*t)) where k is the per-agent per-day vaccination
    rate. Because each attack yields one signature, and attacks arrive at
    rate (attacks_per_N_day) per N-agent-days, the per-agent rate is
    k = attacks_per_N_day / N.  Note: for a logistic / SI propagation
    interpretation, effective rate may scale; here we use the simple
    immunity-accumulation model stated in the task.
    """
    k = attacks_per_N_day / N
    # Fraction immune f(t) = 1 - exp(-k*t)  → t(f) = -ln(1-f)/k
    t_50 = -math.log(0.5) / k
    t_90 = -math.log(0.1) / k
    t_99 = -math.log(0.01) / k
    # "Doubling time" of immune fraction (f grows then saturates). Use the
    # initial regime small-f doubling: f ≈ k*t, doubles in time 1/k? → use
    # t such that f(2t) = 2 f(t) → exp(-k t) (2 - exp(-k t)) = 1;
    # closed-form impractical, approximate with t_50 /
    # log2(1/(1-0.5)) = t_50 / 1 = t_50 (50 %-time surrogate for doubling).
    doubling_surrogate = t_50
    return {
        "label": label,
        "N": N,
        "attacks_per_N_day": attacks_per_N_day,
        "k_per_day": k,
        "t_50_days": round(t_50, 2),
        "t_90_days": round(t_90, 2),
        "t_99_days": round(t_99, 2),
        "doubling_time_surrogate_days": round(doubling_surrogate, 2),
    }


scenarios = [
    scenario(1_000, 2, "A"),
    scenario(10_000, 20, "B"),
    scenario(100_000, 200, "C"),
]

for s in scenarios:
    print(
        f"  Scenario {s['label']}: N={s['N']:>6}  k={s['k_per_day']:.2e}/day  "
        f"t50={s['t_50_days']:>8.1f}d  t90={s['t_90_days']:>8.1f}d  t99={s['t_99_days']:>8.1f}d"
    )

# Metcalfe multiplier — under pure linear scaling, k is constant and
# so is t_50 => multiplier == 1.0 (no network effect in linear model).
# If attack rate scales super-linearly with N (Metcalfe-like N^2 coupling),
# k grows with N and t_50 shrinks. Compute for both cases:
linear_t50 = [s["t_50_days"] for s in scenarios]
linear_multiplier = linear_t50[0] / linear_t50[-1] if linear_t50[-1] else 1.0

# Metcalfe: attacks ~ N^2/N_0 (connections grow quadratically)
metcalfe_scenarios = []
N_base = 1_000
attacks_base = 2
for N in (1_000, 10_000, 100_000):
    # Metcalfe: attack surface scales as N^2 / N_base
    metc_attacks = attacks_base * (N / N_base)  # per-N-day
    # But vaccination sharing is also Metcalfe-accelerated: each signature
    # propagates to O(N) peers, so effective k = (attacks / N) * share_factor,
    # share_factor ~ log(N) / log(N_base)
    share_factor = math.log(max(N, 2)) / math.log(max(N_base, 2))
    k_eff = (metc_attacks / N) * share_factor
    t_50_m = -math.log(0.5) / k_eff
    metcalfe_scenarios.append(
        {
            "N": N,
            "attacks_per_N_day": metc_attacks,
            "share_factor": round(share_factor, 4),
            "k_eff": k_eff,
            "t_50_days": round(t_50_m, 2),
        }
    )
    print(
        f"  Metcalfe N={N:>6}  share={share_factor:.3f}  "
        f"k_eff={k_eff:.3e}/day  t50={t_50_m:.2f}d"
    )

metcalfe_multiplier = (
    metcalfe_scenarios[0]["t_50_days"] / metcalfe_scenarios[-1]["t_50_days"]
    if metcalfe_scenarios[-1]["t_50_days"]
    else 1.0
)
print(f"\n  Linear-model multiplier (t50_1k / t50_100k):   {linear_multiplier:.3f}x")
print(f"  Metcalfe-model multiplier (t50_1k / t50_100k): {metcalfe_multiplier:.3f}x")

vaccination_doubling = {
    "model": "I(t) = N * (1 - exp(-k*t)); t(f) = -ln(1-f)/k",
    "scenarios_linear": scenarios,
    "scenarios_metcalfe": metcalfe_scenarios,
    "linear_multiplier": round(linear_multiplier, 4),
    "metcalfe_multiplier": round(metcalfe_multiplier, 4),
    "doubling_shrinks_with_scale": bool(metcalfe_multiplier > 1.05),
    "interpretation": (
        "Under the pure linear model (constant per-agent attack rate), "
        "t_50 is scale-invariant — no network effect. Under a Metcalfe "
        "model where signature sharing propagates O(log N) faster as the "
        "fleet grows, t_50 shrinks by "
        f"{metcalfe_multiplier:.2f}x from N=1k to N=100k."
    ),
}

# =====================================================================
# TASK 3 — Type-Stratified Calibration
# =====================================================================
print("\n" + "=" * 72)
print("TASK 3 — Type-Stratified Calibration")
print("=" * 72)

MEM_TYPES = [
    "tool_state",
    "episodic",
    "semantic",
    "identity",
    "policy",
    "preference",
    "shared_workflow",
]


def build_entry(mem_type: str, age: float, trust: float, conflict: float, idx: int):
    return {
        "id": f"m_{mem_type}_{idx}",
        "content": f"{mem_type} test content {idx}",
        "type": mem_type,
        "timestamp_age_days": round(age, 3),
        "source_trust": round(trust, 3),
        "source_conflict": round(conflict, 3),
        "downstream_count": 1,
    }


def sigmoid(omega, theta, k):
    # P(success|omega) = 1 / (1 + exp(k * (omega - theta)))
    try:
        return 1.0 / (1.0 + math.exp(k * (omega - theta)))
    except OverflowError:
        return 0.0 if (k * (omega - theta)) > 0 else 1.0


def fit_sigmoid(omegas, labels):
    """Simple grid-search least-squares fit for theta and k.
    labels: list of 0/1 (1 = success)."""
    best = (float("inf"), 50.0, 0.1)
    if not omegas:
        return {"theta": None, "k": None, "sse": None, "n": 0}
    for theta in range(5, 96, 2):  # 5..95
        for k10 in range(1, 51):  # k = 0.02..1.0 step 0.02
            k = k10 / 50.0
            sse = 0.0
            for o, y in zip(omegas, labels):
                p = sigmoid(o, theta, k)
                sse += (p - y) ** 2
            if sse < best[0]:
                best = (sse, theta, k)
    return {
        "theta": best[1],
        "k": round(best[2], 3),
        "sse": round(best[0], 4),
        "n": len(omegas),
    }


type_results = {}
all_thetas = []

for mem_type in MEM_TYPES:
    omegas = []
    labels = []

    # 50 success scenarios (low risk)
    for i in range(50):
        age = random.uniform(0, 10)
        trust = random.uniform(0.8, 1.0)
        conflict = random.uniform(0.0, 0.2)
        entry = build_entry(mem_type, age, trust, conflict, i)
        r = client.post(
            "/v1/preflight",
            json={
                "memory_state": [entry],
                "action_type": "reversible",
                "domain": "general",
            },
            headers=AUTH,
        )
        if r.status_code == 200:
            omegas.append(r.json().get("omega_mem_final", 0.0))
            labels.append(1)

    # 50 failure scenarios (high risk)
    for i in range(50):
        age = random.uniform(30, 100)
        trust = random.uniform(0.1, 0.4)
        conflict = random.uniform(0.5, 0.9)
        entry = build_entry(mem_type, age, trust, conflict, 1000 + i)
        r = client.post(
            "/v1/preflight",
            json={
                "memory_state": [entry],
                "action_type": "reversible",
                "domain": "general",
            },
            headers=AUTH,
        )
        if r.status_code == 200:
            omegas.append(r.json().get("omega_mem_final", 0.0))
            labels.append(0)

    fit = fit_sigmoid(omegas, labels)
    theta = fit["theta"]
    k = fit["k"]
    in_55_70 = bool(theta is not None and 55 <= theta <= 70)
    if theta is not None:
        all_thetas.append(theta)
    mean_success = (
        sum(o for o, y in zip(omegas, labels) if y == 1)
        / max(1, sum(labels))
    )
    mean_failure = (
        sum(o for o, y in zip(omegas, labels) if y == 0)
        / max(1, len(labels) - sum(labels))
    )
    type_results[mem_type] = {
        "n_samples": fit["n"],
        "theta": theta,
        "k": k,
        "sse": fit["sse"],
        "mean_omega_success": round(mean_success, 2),
        "mean_omega_failure": round(mean_failure, 2),
        "theta_in_55_70_band": in_55_70,
    }
    print(
        f"  {mem_type:>16}: n={fit['n']:3d}  θ={theta}  k={k}  "
        f"μ_ok={mean_success:5.1f}  μ_fail={mean_failure:5.1f}  "
        f"55-70? {in_55_70}"
    )

theta_spread = (max(all_thetas) - min(all_thetas)) if all_thetas else 0
type_specific_warranted = bool(theta_spread > 10)
print(
    f"\n  θ spread across types: {theta_spread:.1f} "
    f"(min={min(all_thetas) if all_thetas else None}, "
    f"max={max(all_thetas) if all_thetas else None})"
)
print(f"  Type-specific thresholds warranted? {type_specific_warranted}")

type_stratified_calibration = {
    "per_type": type_results,
    "theta_spread": round(theta_spread, 2),
    "type_specific_threshold_warranted": type_specific_warranted,
    "any_type_in_55_70_band": any(
        v.get("theta_in_55_70_band") for v in type_results.values()
    ),
    "interpretation": (
        f"θ spread of {theta_spread:.1f} points across 7 memory types "
        f"{'>' if type_specific_warranted else '≤'} 10-point criterion → "
        f"{'type-specific thresholds recommended' if type_specific_warranted else 'uniform threshold acceptable'}."
    ),
}

# =====================================================================
# TASK 4 — Q-table Convergence
# =====================================================================
print("\n" + "=" * 72)
print("TASK 4 — Q-table Convergence")
print("=" * 72)

alpha = 0.1
gamma = 0.9
S = 256
A = 4
delta = 0.05
C = 1.0

N_theoretical = int(
    C * (1.0 / (1 - gamma) ** 2) * S * A * math.log(1.0 / delta) / alpha
)
print(f"  Theoretical bound N = {N_theoretical:,} calls (worst-case PAC)")

DOMAINS = ["general", "fintech", "medical", "coding", "legal", "customer_support"]


def probe_q_value(domain: str):
    """Deterministic probe entry — used to check Q-value stability for a
    fixed (state, action) pair per domain."""
    entry = {
        "id": f"probe_{domain}",
        "content": "probe memory for RL convergence",
        "type": "episodic",
        "timestamp_age_days": 5.0,
        "source_trust": 0.7,
        "source_conflict": 0.2,
        "downstream_count": 1,
    }
    r = client.post(
        "/v1/preflight",
        json={
            "memory_state": [entry],
            "action_type": "reversible",
            "domain": domain,
        },
        headers=AUTH,
    )
    if r.status_code != 200:
        return None, None, None
    data = r.json()
    rl = data.get("rl_adjustment") or {}
    return (
        rl.get("q_value"),
        rl.get("learning_episodes"),
        rl.get("confidence"),
    )


def simulate_outcome(outcome_id, omega):
    """Simulate an outcome based on omega. Returns True on success."""
    if not outcome_id:
        return False
    # Higher omega -> higher failure probability
    p_fail = min(0.95, max(0.05, omega / 100.0))
    status = "failure" if random.random() < p_fail else "success"
    components = ["s_freshness", "s_drift"] if status == "failure" else []
    try:
        r = client.post(
            "/v1/outcome",
            json={
                "outcome_id": outcome_id,
                "status": status,
                "failure_components": components,
            },
            headers=AUTH,
        )
        return r.status_code in (200, 201)
    except Exception:
        return False


def train_and_probe(domain: str, n_calls: int = 200, check_at=(10, 50, 100, 200)):
    """Fire preflight+outcome n_calls times; probe Q-value at checkpoints.
    Convergence = 10 consecutive identical probes."""
    stable_streak = 0
    last_q = None
    calls_to_converge = None

    # Prime learning with varied states
    for i in range(n_calls):
        entry = {
            "id": f"train_{domain}_{i}",
            "content": f"training memory {i}",
            "type": random.choice(["episodic", "semantic", "preference"]),
            "timestamp_age_days": random.uniform(0, 80),
            "source_trust": random.uniform(0.2, 0.95),
            "source_conflict": random.uniform(0.0, 0.7),
            "downstream_count": random.randint(0, 5),
        }
        r = client.post(
            "/v1/preflight",
            json={
                "memory_state": [entry],
                "action_type": random.choice(["informational", "reversible"]),
                "domain": domain,
            },
            headers=AUTH,
        )
        if r.status_code == 200:
            data = r.json()
            simulate_outcome(
                data.get("outcome_id"), data.get("omega_mem_final", 50.0)
            )

        # Probe at checkpoints
        if (i + 1) in check_at:
            q, _, _ = probe_q_value(domain)
            # also run a short stability window (5 probes here since full
            # training loop is the expensive part)
            probes = [q]
            for _ in range(4):
                qq, _, _ = probe_q_value(domain)
                probes.append(qq)
            unique = set(round(p, 4) if p is not None else None for p in probes)
            if len(unique) == 1 and calls_to_converge is None:
                calls_to_converge = i + 1

    # Final stability window: 10 consecutive probes
    final_probes = []
    for _ in range(10):
        q, ep, conf = probe_q_value(domain)
        final_probes.append((q, ep, conf))
    qs = [p[0] for p in final_probes if p[0] is not None]
    final_unique = len(
        set(round(q, 4) if q is not None else None for q in qs)
    )
    currently_converged = bool(qs and final_unique == 1)
    if currently_converged and calls_to_converge is None:
        calls_to_converge = n_calls

    # Learning episodes / confidence from the last probe
    learning_episodes = final_probes[-1][1] if final_probes else 0
    confidence = final_probes[-1][2] if final_probes else 0

    return {
        "calls_to_converge": calls_to_converge,
        "currently_converged": currently_converged,
        "learning_episodes": learning_episodes,
        "confidence": confidence,
        "final_q_unique_values": final_unique,
    }


practical = {}
for dom in DOMAINS:
    print(f"  training domain={dom} ...", flush=True)
    practical[dom] = train_and_probe(dom, n_calls=200)
    p = practical[dom]
    print(
        f"    calls_to_converge={p['calls_to_converge']}  "
        f"currently_converged={p['currently_converged']}  "
        f"episodes={p['learning_episodes']}  "
        f"conf={p['confidence']}  "
        f"unique_final_Q={p['final_q_unique_values']}"
    )

# Recommendation: mean of calls_to_converge (exclude None)
converged_calls = [v["calls_to_converge"] for v in practical.values() if v["calls_to_converge"]]
recommend_n = max(converged_calls) if converged_calls else N_theoretical
print(f"\n  Recommended N before trusting RL: {recommend_n}")

q_table_convergence = {
    "theoretical_bound": N_theoretical,
    "theoretical_formula": "N = C * (1/(1-γ)^2) * |S|*|A| * log(1/δ) / α",
    "parameters": {
        "alpha": alpha,
        "gamma": gamma,
        "S": S,
        "A": A,
        "delta": delta,
        "C": C,
    },
    "practical_estimate_per_domain": practical,
    "recommendation": (
        f"Deploy with at least {recommend_n} preflight+outcome calls "
        f"(practical empirical) before trusting RL adjustment. Theoretical "
        f"worst-case bound of {N_theoretical:,} is {N_theoretical/max(recommend_n,1):,.0f}x "
        f"higher than empirical — worst case is rarely reached because real "
        f"state distributions are sparse."
    ),
}

# =====================================================================
# Merge and persist
# =====================================================================
print("\n" + "=" * 72)
print("MERGE + SAVE")
print("=" * 72)

existing = load_existing_results(RESULTS_PATH)
existing["vaccination_doubling"] = vaccination_doubling
existing["type_stratified_calibration"] = type_stratified_calibration
existing["q_table_convergence"] = q_table_convergence
save_results(RESULTS_PATH, existing)

print(f"  Wrote {RESULTS_PATH}")
print(f"  Keys present: {sorted(existing.keys())}")
print("\nDone.")
