#!/usr/bin/env python3
"""
Energy Lifetime Experiment — Sgraal Scoring Engine
Computes entropy production σ per memory type, F/σ lifetime,
healing energy recovery, and energy-age relationship.
"""

import os, sys, json

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

F_BASELINE = 80.6126

MEMORY_TYPES = {
    "tool_state":  0.15,
    "episodic":    0.05,
    "semantic":    0.02,
    "identity":    0.002,
}

def make_entry(mem_type, age, trust=0.8, conflict=0.1, entry_id="entry_1"):
    return {
        "id": entry_id,
        "content": f"Test {mem_type} entry at age {age}",
        "type": mem_type,
        "timestamp_age_days": age,
        "source_trust": trust,
        "source_conflict": conflict,
        "downstream_count": 3,
    }


def run_preflight(entry, score_history, domain="general", action_type="reversible"):
    payload = {
        "memory_state": [entry],
        "action_type": action_type,
        "domain": domain,
        "score_history": score_history,
    }
    r = client.post("/v1/preflight", headers=AUTH, json=payload)
    return r.json()


# ═══════════════════════════════════════════════════════════════
# TASK 1 — Compute σ (entropy_production) per memory type
# ═══════════════════════════════════════════════════════════════
print("=" * 70)
print("TASK 1 — Entropy Production (σ) per Memory Type")
print("=" * 70)

per_type_results = {}

for mem_type, lam in MEMORY_TYPES.items():
    print(f"\n--- {mem_type} (λ={lam}) ---")
    score_history = [50.0] * 10  # seed
    sigmas = []

    for day in range(1, 21):
        entry = make_entry(mem_type, age=day)
        data = run_preflight(entry, score_history)

        omega = data.get("omega_mem_final", 50.0)
        score_history.append(omega)
        # keep last 50 to avoid huge payloads
        if len(score_history) > 50:
            score_history = score_history[-50:]

        info_thermo = data.get("info_thermodynamics", {})
        sigma = info_thermo.get("entropy_production")

        if sigma is not None:
            sigmas.append(sigma)
            print(f"  day={day:2d}  omega={omega:.2f}  σ={sigma:.6f}")
        else:
            print(f"  day={day:2d}  omega={omega:.2f}  σ=N/A")

    mean_sigma = sum(sigmas) / len(sigmas) if sigmas else 0.0
    f_over_sigma = F_BASELINE / mean_sigma if mean_sigma > 0 else float("inf")
    days_until = f_over_sigma  # 1 call/day assumption

    per_type_results[mem_type] = {
        "lambda": lam,
        "mean_sigma": round(mean_sigma, 6),
        "F_over_sigma": round(f_over_sigma, 2),
        "days_until_entropy_death": round(days_until, 2),
        "sigma_samples": len(sigmas),
    }

    print(f"  => mean σ = {mean_sigma:.6f}")
    print(f"  => F/σ = {f_over_sigma:.2f} calls")
    print(f"  => days until entropy death = {days_until:.2f}")


# ═══════════════════════════════════════════════════════════════
# TASK 2 — F/σ summary (already computed above)
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TASK 2 — F/σ Summary (Remaining Calls Before Max Entropy)")
print("=" * 70)

for mem_type, res in per_type_results.items():
    print(f"  {mem_type:15s}  σ={res['mean_sigma']:.6f}  F/σ={res['F_over_sigma']:.2f}  days={res['days_until_entropy_death']:.2f}")


# ═══════════════════════════════════════════════════════════════
# TASK 3 — Healing Energy Recovery
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TASK 3 — Healing Energy Recovery (delta_F)")
print("=" * 70)

healing_recovery = {}

for mem_type, lam in MEMORY_TYPES.items():
    print(f"\n--- {mem_type} ---")
    score_history = [50.0] * 10

    # Step 1: degraded entry (high age, low trust)
    degraded_entry = make_entry(mem_type, age=60, trust=0.3, conflict=0.5, entry_id="heal_target")
    data_before = run_preflight(degraded_entry, score_history)
    F_before = data_before.get("free_energy", {}).get("F", 0.0)
    omega_before = data_before.get("omega_mem_final", 0.0)
    print(f"  BEFORE heal: omega={omega_before:.2f}, F={F_before:.4f}")

    # Step 2: call heal
    heal_r = client.post("/v1/heal", headers=AUTH, json={
        "entry_id": "heal_target",
        "action": "REFETCH",
    })
    heal_data = heal_r.json()
    print(f"  Heal response: {heal_data.get('healed', False)}, counter={heal_data.get('healing_counter', 0)}")

    # Step 3: healed entry (reset age, improved trust)
    healed_entry = make_entry(mem_type, age=0, trust=0.9, conflict=0.05, entry_id="heal_target")
    # append omega_before to history
    score_history_after = score_history + [omega_before]
    data_after = run_preflight(healed_entry, score_history_after)
    F_after = data_after.get("free_energy", {}).get("F", 0.0)
    omega_after = data_after.get("omega_mem_final", 0.0)
    print(f"  AFTER  heal: omega={omega_after:.2f}, F={F_after:.4f}")

    delta_F = F_after - F_before
    print(f"  delta_F = {delta_F:.4f} ({'recovered' if delta_F > 0 else 'lost' if delta_F < 0 else 'unchanged'})")

    healing_recovery[mem_type] = {
        "F_before": round(F_before, 4),
        "F_after": round(F_after, 4),
        "delta_F": round(delta_F, 4),
        "omega_before": round(omega_before, 2),
        "omega_after": round(omega_after, 2),
    }


# ═══════════════════════════════════════════════════════════════
# TASK 4 — Energy-Age Relationship (tool_state)
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TASK 4 — Energy-Age Curve (tool_state)")
print("=" * 70)

ages = [0, 1, 2, 3, 5, 7, 10, 15, 20, 30, 45, 60, 75, 90]
f_values = []
score_history = [50.0] * 10

for age in ages:
    entry = make_entry("tool_state", age=age)
    data = run_preflight(entry, score_history)

    omega = data.get("omega_mem_final", 50.0)
    F_val = data.get("free_energy", {}).get("F", 0.0)
    f_values.append(round(F_val, 4))

    score_history.append(omega)
    if len(score_history) > 50:
        score_history = score_history[-50:]

    print(f"  age={age:3d}d  omega={omega:.2f}  F={F_val:.4f}")

# Determine shape by analyzing the curve
diffs = [f_values[i+1] - f_values[i] for i in range(len(f_values)-1)]
age_diffs = [ages[i+1] - ages[i] for i in range(len(ages)-1)]
rates = [d / a if a > 0 else 0 for d, a in zip(diffs, age_diffs)]

# Check for non-monotonicity (dip then rise)
has_decrease = any(d < -0.1 for d in diffs[:4])  # early decrease
has_increase = any(d > 0.1 for d in diffs[2:8])   # subsequent increase
has_plateau = all(abs(d) < 0.1 for d in diffs[-3:])  # late plateau

if has_decrease and has_increase and has_plateau:
    min_idx = f_values.index(min(f_values))
    shape = f"non-monotonic: dip at age {ages[min_idx]} then saturating rise to plateau ~{f_values[-1]:.2f}"
elif has_plateau and not has_decrease:
    shape = "logarithmic"
elif all(abs(r - rates[0]) < 0.5 for r in rates if rates[0] != 0):
    shape = "linear"
else:
    shape = "exponential"

print(f"\n  Shape classification: {shape}")
print(f"  F range: {min(f_values):.4f} to {max(f_values):.4f}")
print(f"  Rate of change (first 3): {rates[:3]}")
print(f"  Rate of change (last 3): {rates[-3:]}")


# ═══════════════════════════════════════════════════════════════
# Save results
# ═══════════════════════════════════════════════════════════════
results = {
    "F_baseline": F_BASELINE,
    "per_type": per_type_results,
    "healing_recovery": healing_recovery,
    "energy_age_curve": {
        "ages": ages,
        "F_values": f_values,
        "shape": shape,
    },
}

output_path = "/Users/zsobrakpeter/core/research/results/energy_lifetime.json"
with open(output_path, "w") as f:
    json.dump(results, f, indent=2)

print(f"\n{'=' * 70}")
print(f"Results saved to {output_path}")
print(f"{'=' * 70}")
