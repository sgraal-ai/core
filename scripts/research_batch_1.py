#!/usr/bin/env python3
"""Research Batch 1: Healing Budget, Decision Boundary, Per-Axis Temperature, Saturation Constant."""

import os, sys, json, math, random, time
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")

from fastapi.testclient import TestClient
from api.main import app
client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

import numpy as np

random.seed(42)
np.random.seed(42)

# ============================================================
# ITEM 1: Healing Budget
# ============================================================
print("=" * 60)
print("ITEM 1: Healing Budget")
print("=" * 60)

with open("/Users/zsobrakpeter/core/research/results/energy_lifetime.json") as f:
    energy_data = json.load(f)

F_baseline = energy_data["F_baseline"]
healing = energy_data["healing_recovery"]

delta_Fs = {}
for mtype, rec in healing.items():
    delta_Fs[mtype] = abs(rec["delta_F"])

mean_delta_F = np.mean(list(delta_Fs.values()))
total_budget = F_baseline / mean_delta_F

per_type_budgets = {}
for mtype, dF in delta_Fs.items():
    per_type_budgets[mtype] = F_baseline / dF

print(f"  F_baseline = {F_baseline}")
print(f"  |delta_F| per type: {json.dumps({k: round(v, 4) for k, v in delta_Fs.items()}, indent=4)}")
print(f"  mean |delta_F| = {mean_delta_F:.4f}")
print(f"  Total healing budget = {total_budget:.2f} heals")
print(f"  Per-type budgets:")
for k, v in per_type_budgets.items():
    print(f"    {k}: {v:.2f} heals")

healing_budget_result = {
    "F_baseline": F_baseline,
    "mean_delta_F": round(mean_delta_F, 4),
    "total_budget": round(total_budget, 2),
    "per_type": {k: round(v, 2) for k, v in per_type_budgets.items()}
}

# ============================================================
# ITEM 2 & 3: Decision Boundary + Per-Axis Temperature
# (Share the same 500 preflight calls)
# ============================================================
print("\n" + "=" * 60)
print("ITEMS 2 & 3: Generating 500 diverse memory states...")
print("=" * 60)

MEMORY_TYPES = ["tool_state", "episodic", "semantic", "preference", "shared_workflow", "policy", "identity"]
COMPONENT_NAMES = ["s_freshness", "s_drift", "s_provenance", "s_interference", "r_belief"]
AXIS_LABELS = ["Risk", "Decay", "Trust", "Corruption", "Belief"]

records = []  # (5-vector, action)
raw_scores = []  # for PCA

n_total = 500
n_done = 0
n_errors = 0

for i in range(n_total):
    trust = round(random.uniform(0.1, 1.0), 2)
    conflict = round(random.uniform(0.0, 0.9), 2)
    # Ensure trust + conflict <= 1.0 to avoid clipping issues
    if trust + conflict > 1.0:
        conflict = round(1.0 - trust, 2)
    age = round(random.uniform(0, 100), 1)
    downstream = random.randint(1, 20)
    mtype = random.choice(MEMORY_TYPES)

    payload = {
        "memory_state": [{
            "id": f"research_{i}",
            "content": f"Research entry {i} for boundary analysis",
            "type": mtype,
            "timestamp_age_days": age,
            "source_trust": trust,
            "source_conflict": conflict,
            "downstream_count": downstream
        }],
        "action_type": random.choice(["informational", "reversible", "irreversible", "destructive"]),
        "domain": random.choice(["general", "fintech", "medical", "legal", "coding", "customer_support"])
    }

    r = client.post("/v1/preflight", headers=AUTH, json=payload)
    if r.status_code != 200:
        n_errors += 1
        continue

    data = r.json()
    action = data.get("recommended_action", "")
    breakdown = data.get("component_breakdown", {})

    scores = []
    for comp in COMPONENT_NAMES:
        val = breakdown.get(comp, 0.0)
        if isinstance(val, dict):
            val = val.get("value", val.get("score", 0.0))
        scores.append(float(val))

    records.append((scores, action))
    raw_scores.append(scores)
    n_done += 1

    if (i + 1) % 100 == 0:
        print(f"  ... {i+1}/{n_total} done ({n_errors} errors)")

print(f"  Completed {n_done} successful calls ({n_errors} errors)")

# Count actions
from collections import Counter
action_counts = Counter(a for _, a in records)
print(f"  Action distribution: {dict(action_counts)}")

# ---- ITEM 2: Decision Boundary ----
print("\n" + "=" * 60)
print("ITEM 2: Decision Boundary (BLOCK vs non-BLOCK)")
print("=" * 60)

block_vecs = np.array([s for s, a in records if a == "BLOCK"])
non_block_vecs = np.array([s for s, a in records if a != "BLOCK"])

n_block = len(block_vecs)
n_non_block = len(non_block_vecs)
print(f"  BLOCK: {n_block}, non-BLOCK: {n_non_block}")

if n_block >= 2 and n_non_block >= 2:
    mean_block = block_vecs.mean(axis=0)
    mean_non_block = non_block_vecs.mean(axis=0)

    normal = mean_block - mean_non_block
    norm_len = np.linalg.norm(normal)
    if norm_len > 1e-10:
        normal = normal / norm_len

    # Threshold = midpoint projection
    mid = (mean_block + mean_non_block) / 2.0
    threshold = np.dot(normal, mid)

    # Test accuracy
    correct = 0
    for scores, action in records:
        proj = np.dot(normal, scores)
        predicted_block = proj > threshold
        actual_block = action == "BLOCK"
        if predicted_block == actual_block:
            correct += 1
    accuracy = correct / len(records)

    weights_dict = {}
    for j, label in enumerate(AXIS_LABELS):
        weights_dict[label.lower()] = round(float(normal[j]), 6)

    print(f"  Weights: {weights_dict}")
    print(f"  Threshold (theta): {threshold:.6f}")
    print(f"  Accuracy: {accuracy:.4f} ({correct}/{len(records)})")
    print(f"  Equation: {' + '.join(f'{normal[j]:.4f}*{AXIS_LABELS[j]}' for j in range(5))} > {threshold:.4f} => BLOCK")
else:
    print("  WARNING: Not enough BLOCK or non-BLOCK samples for boundary fitting")
    weights_dict = {l.lower(): 0.0 for l in AXIS_LABELS}
    threshold = 0.0
    accuracy = 0.0

decision_boundary_result = {
    "weights": weights_dict,
    "threshold": round(float(threshold), 6),
    "equation": " + ".join(f"w_{AXIS_LABELS[j].lower()}*{AXIS_LABELS[j]}" for j in range(5)) + " > theta",
    "accuracy": round(float(accuracy), 4),
    "n_samples": n_done,
    "n_block": n_block,
    "n_non_block": n_non_block
}

# ---- ITEM 3: Per-Axis Temperature ----
print("\n" + "=" * 60)
print("ITEM 3: Per-Axis Temperature via PCA")
print("=" * 60)

X = np.array(raw_scores)
# Center
X_centered = X - X.mean(axis=0)

# PCA via SVD
U, S, Vt = np.linalg.svd(X_centered, full_matrices=False)
eigenvalues = (S ** 2) / (len(X) - 1)
total_var = eigenvalues.sum()

# Project onto PCs
PC_scores = X_centered @ Vt.T

axes_result = []
for i in range(min(5, len(eigenvalues))):
    var_i = float(eigenvalues[i])
    var_explained = var_i / total_var
    # Temperature = variance along this PC (equipartition: E = 0.5 * k * T, so T = 2*E/k = 2*var with k=1)
    temperature_i = 2.0 * var_i

    # Dominant component: highest absolute loading
    loadings = Vt[i]
    dominant_idx = int(np.argmax(np.abs(loadings)))
    dominant_comp = COMPONENT_NAMES[dominant_idx]

    axes_result.append({
        "pc": i + 1,
        "temperature": round(temperature_i, 4),
        "dominant_component": dominant_comp,
        "variance_explained": round(var_explained, 4),
        "eigenvalue": round(var_i, 4),
        "loadings": {COMPONENT_NAMES[j]: round(float(loadings[j]), 4) for j in range(5)}
    })

    print(f"  PC{i+1}: T={temperature_i:.4f}, var_explained={var_explained:.4f}, dominant={dominant_comp}")
    print(f"         loadings: {', '.join(f'{COMPONENT_NAMES[j]}={loadings[j]:.3f}' for j in range(5))}")

temps = [a["temperature"] for a in axes_result]
hottest_idx = int(np.argmax(temps))
coldest_idx = int(np.argmin(temps))
temp_ratio = max(temps) / min(temps) if min(temps) > 0 else float("inf")

print(f"\n  Hottest axis: PC{hottest_idx+1} ({axes_result[hottest_idx]['dominant_component']}) T={temps[hottest_idx]:.4f}")
print(f"  Coldest axis: PC{coldest_idx+1} ({axes_result[coldest_idx]['dominant_component']}) T={temps[coldest_idx]:.4f}")
print(f"  Temperature ratio (hot/cold): {temp_ratio:.2f}")

per_axis_temp_result = {
    "axes": axes_result,
    "hottest_axis": axes_result[hottest_idx]["dominant_component"],
    "coldest_axis": axes_result[coldest_idx]["dominant_component"],
    "temperature_ratio": round(temp_ratio, 4)
}

# ============================================================
# ITEM 4: Saturation Constant
# ============================================================
print("\n" + "=" * 60)
print("ITEM 4: Saturation Constant (max staleness, free energy)")
print("=" * 60)

score_history = [50, 55, 60, 65, 70, 75, 80, 85, 80, 75]

# By type (domain=general)
by_type = {}
for mtype in MEMORY_TYPES:
    payload = {
        "memory_state": [{
            "id": f"sat_{mtype}",
            "content": f"Saturation test entry for {mtype}",
            "type": mtype,
            "timestamp_age_days": 365,
            "source_trust": 0.5,
            "source_conflict": 0.5,
            "downstream_count": 5
        }],
        "action_type": "irreversible",
        "domain": "general",
        "score_history": score_history
    }
    r = client.post("/v1/preflight", headers=AUTH, json=payload)
    data = r.json()
    fe = data.get("free_energy", {})
    F_val = fe.get("F", None)
    by_type[mtype] = F_val
    print(f"  {mtype}: F = {F_val}")

# By domain (type=semantic, age=365)
by_domain = {}
for domain in ["general", "fintech", "medical"]:
    payload = {
        "memory_state": [{
            "id": f"sat_{domain}",
            "content": f"Saturation test entry for domain {domain}",
            "type": "semantic",
            "timestamp_age_days": 365,
            "source_trust": 0.5,
            "source_conflict": 0.5,
            "downstream_count": 5
        }],
        "action_type": "irreversible",
        "domain": domain,
        "score_history": score_history
    }
    r = client.post("/v1/preflight", headers=AUTH, json=payload)
    data = r.json()
    fe = data.get("free_energy", {})
    F_val = fe.get("F", None)
    by_domain[domain] = F_val
    print(f"  domain={domain}: F = {F_val}")

# Statistics
all_F = [v for v in list(by_type.values()) + list(by_domain.values()) if v is not None]
mean_F = float(np.mean(all_F)) if all_F else 0.0
std_F = float(np.std(all_F)) if all_F else 0.0
cv = std_F / mean_F if mean_F > 0 else float("inf")
universal = cv < 0.1  # <10% coefficient of variation = "universal"

print(f"\n  All F values: {[round(v, 4) if v else None for v in all_F]}")
print(f"  Mean F = {mean_F:.4f}")
print(f"  Std F = {std_F:.4f}")
print(f"  CV = {cv:.4f}")
print(f"  Universal (CV < 10%): {universal}")

saturation_result = {
    "by_type": {k: round(v, 4) if v is not None else None for k, v in by_type.items()},
    "by_domain": {k: round(v, 4) if v is not None else None for k, v in by_domain.items()},
    "mean": round(mean_F, 4),
    "std": round(std_F, 4),
    "coefficient_of_variation": round(cv, 4),
    "universal": universal
}

# ============================================================
# SAVE RESULTS
# ============================================================
print("\n" + "=" * 60)
print("Saving results...")
print("=" * 60)

results = {
    "healing_budget": healing_budget_result,
    "decision_boundary": decision_boundary_result,
    "per_axis_temperature": per_axis_temp_result,
    "saturation_constant": saturation_result
}

outpath = "/Users/zsobrakpeter/core/research/results/ten_findings_batch1.json"

# Replace inf/nan with string representations for valid JSON
def sanitize(obj):
    if isinstance(obj, float):
        if math.isinf(obj):
            return "Infinity"
        if math.isnan(obj):
            return "NaN"
    elif isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize(v) for v in obj]
    return obj

with open(outpath, "w") as f:
    json.dump(sanitize(results), f, indent=2)

print(f"Results saved to {outpath}")
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  Item 1 - Healing Budget: {total_budget:.2f} heals (mean |dF|={mean_delta_F:.4f})")
print(f"  Item 2 - Decision Boundary: accuracy={accuracy:.4f}, {n_block} BLOCK / {n_non_block} non-BLOCK")
print(f"  Item 3 - Temperature ratio: {temp_ratio:.2f}x (hottest={axes_result[hottest_idx]['dominant_component']}, coldest={axes_result[coldest_idx]['dominant_component']})")
print(f"  Item 4 - Saturation: mean F={mean_F:.4f}, std={std_F:.4f}, universal={universal}")
