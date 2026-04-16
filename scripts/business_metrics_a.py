#!/usr/bin/env python3
"""Business Metrics A: Expected Savings per BLOCK (TASK 1) + Hidden Decision Boundaries (TASK 5).

Appends/merges into /Users/zsobrakpeter/core/research/results/business_metrics.json
with keys 'expected_savings' and 'decision_boundaries'.
"""

import os, sys, json, math, random
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

random.seed(42)

RESULTS_PATH = "/Users/zsobrakpeter/core/research/results/business_metrics.json"
CALIB_PATH = "/Users/zsobrakpeter/core/research/results/calibration_curve.json"
OUTCOME_PATH = "/Users/zsobrakpeter/core/research/results/omega_outcome_results.json"
BATCH1_PATH = "/Users/zsobrakpeter/core/research/results/ten_findings_batch1.json"


# ------------------------------------------------------------------
# TASK 1 — Expected Savings per BLOCK
# ------------------------------------------------------------------
print("=" * 60)
print("TASK 1: Expected Savings per BLOCK")
print("=" * 60)

# --- Load calibration curve if present ---
calib_curve = None
method_note = None
if os.path.exists(CALIB_PATH):
    try:
        with open(CALIB_PATH) as f:
            calib_json = json.load(f)
        calib_curve = calib_json.get("curve", None)
        method_note = "calibration curve (per-band P(success) from calibration_curve.json, sigmoid fallback for empty bands)"
    except Exception as e:
        print(f"  calibration_curve.json load failed: {e}")

if calib_curve is None:
    method_note = "sigmoid fit, theta=46, k=0.15"

# Sigmoid fallback
THETA = 46.0
K = 0.15


def p_failure_sigmoid(omega: float) -> float:
    # P(failure|omega) = 1 / (1 + exp(-k*(omega - theta)))
    return 1.0 / (1.0 + math.exp(-K * (omega - THETA)))


def p_failure_for_band(band_label: str, omega_mid: float) -> float:
    """Return P(failure) from calibration curve if available, else sigmoid."""
    if calib_curve is not None and band_label in calib_curve:
        entry = calib_curve[band_label]
        n = entry.get("n", 0)
        if n >= 2:
            return 1.0 - float(entry.get("p_success", 0.5))
    return p_failure_sigmoid(omega_mid)


# --- Domain defaults ---
AVG_TX_VALUE = {
    "fintech": 1000.0,
    "medical": 5000.0,
    "legal": 2000.0,
    "coding": 100.0,
    "customer_support": 50.0,
    "general": 200.0,
}

# Focus combos
FOCUS_OMEGAS = [35, 50, 65, 75, 85]
FOCUS_DOMAINS = ["fintech", "medical", "legal"]
BAND_FOR_OMEGA = {
    35: "30-40",
    50: "50-60",
    65: "60-70",
    75: "70-80",
    85: "80-90",
}

BLOCK_RATE_PER_DAY = 3.0  # blocks/agent/day default

per_band_domain = {}
for omega in FOCUS_OMEGAS:
    band_label = BAND_FOR_OMEGA[omega]
    p_fail = p_failure_for_band(band_label, omega)
    for domain in FOCUS_DOMAINS:
        tx = AVG_TX_VALUE[domain]
        expected_savings = p_fail * tx
        annual_100 = expected_savings * BLOCK_RATE_PER_DAY * 100.0 * 365.0
        key = f"omega_{omega}_{domain}"
        per_band_domain[key] = {
            "omega_band": band_label,
            "P_failure": round(p_fail, 4),
            "avg_transaction_value": tx,
            "expected_savings_per_block": round(expected_savings, 2),
            "annual_savings_100_agents": round(annual_100, 2),
        }
        print(
            f"  {key:30s}  P_fail={p_fail:.3f}  $/block={expected_savings:8.2f}  "
            f"annual_100ag=${annual_100:,.0f}"
        )

# --- Fleet 1000 agents annual savings, 1% block rate ---
# Assumption: 1% of calls result in BLOCK. Calls per agent per day assumed 100
# (so 1% => 1 block/agent/day). Let's be explicit and use the same BLOCK_RATE_PER_DAY
# interpretation as TASK 1: 1% block rate over 100 calls/day/agent = 1 block/agent/day.
# BUT the prompt says "1% of calls result in a BLOCK". We'll assume 100 calls/agent/day.
# So blocks/agent/day = 100 * 0.01 = 1.
CALLS_PER_AGENT_PER_DAY = 100
BLOCK_FRACTION = 0.01
blocks_per_agent_per_day_fleet = CALLS_PER_AGENT_PER_DAY * BLOCK_FRACTION  # 1.0

# Per-domain: use weighted P(failure) averaged over the full calibration curve (realistic mix).
# Weight each omega band by calibration n; fall back to uniform over FOCUS_OMEGAS.
if calib_curve is not None:
    total_n = sum(b.get("n", 0) for b in calib_curve.values())
    if total_n > 0:
        weighted_p_fail = 0.0
        for band, entry in calib_curve.items():
            n = entry.get("n", 0)
            if n <= 0:
                continue
            try:
                lo, hi = band.split("-")
                mid = (float(lo) + float(hi)) / 2.0
            except Exception:
                mid = 50.0
            pf = 1.0 - float(entry.get("p_success", 0.5))
            weighted_p_fail += (n / total_n) * pf
    else:
        weighted_p_fail = p_failure_sigmoid(50.0)
else:
    weighted_p_fail = p_failure_sigmoid(50.0)

print(f"\n  Weighted P(failure) across all omega bands = {weighted_p_fail:.4f}")
print(f"  Fleet assumption: 1000 agents, {CALLS_PER_AGENT_PER_DAY} calls/agent/day, 1% BLOCK rate")

NUM_AGENTS = 1000
per_domain_annual = {}
for domain, tx in AVG_TX_VALUE.items():
    savings_per_block = weighted_p_fail * tx
    annual = (
        savings_per_block
        * blocks_per_agent_per_day_fleet
        * NUM_AGENTS
        * 365.0
    )
    per_domain_annual[domain] = round(annual, 2)
    print(f"    {domain:20s}  ${annual:,.0f}")

# Headline: sum across domains assuming equal traffic split (6 domains)
# OR alternative: weighted by a default distribution. Use equal split for headline.
equal_weight = 1.0 / len(AVG_TX_VALUE)
blended_tx = sum(tx * equal_weight for tx in AVG_TX_VALUE.values())
total_annual_savings = (
    weighted_p_fail
    * blended_tx
    * blocks_per_agent_per_day_fleet
    * NUM_AGENTS
    * 365.0
)
print(f"\n  Headline: total annual savings (1000 agents, equal domain mix) = ${total_annual_savings:,.0f}")

expected_savings_result = {
    "method": method_note,
    "assumptions": {
        "sigmoid_theta": THETA,
        "sigmoid_k": K,
        "block_rate_per_day_per_agent": BLOCK_RATE_PER_DAY,
        "avg_transaction_value_usd": AVG_TX_VALUE,
    },
    "per_band_domain": per_band_domain,
    "fleet_1000_agents_annual_savings": {
        "assumptions": (
            f"1% block rate, {CALLS_PER_AGENT_PER_DAY} calls/agent/day "
            f"=> {blocks_per_agent_per_day_fleet} blocks/agent/day, "
            f"default transaction values, equal domain mix for headline, "
            f"weighted P(failure)={weighted_p_fail:.4f} from calibration curve"
        ),
        "weighted_p_failure": round(weighted_p_fail, 4),
        "blocks_per_agent_per_day": blocks_per_agent_per_day_fleet,
        "num_agents": NUM_AGENTS,
        "total_annual_savings_usd": round(total_annual_savings, 2),
        "per_domain": per_domain_annual,
    },
}


# ------------------------------------------------------------------
# TASK 5 — Hidden Decision Boundaries
# ------------------------------------------------------------------
print("\n" + "=" * 60)
print("TASK 5: Hidden Decision Boundaries (500 samples)")
print("=" * 60)

MEMORY_TYPES = [
    "tool_state", "episodic", "semantic", "preference",
    "shared_workflow", "policy", "identity",
]
COMPONENT_NAMES = ["s_freshness", "s_drift", "s_provenance", "s_interference", "r_belief"]
AXIS_LABELS = ["risk", "decay", "trust", "corruption", "belief"]


def extract_component(breakdown, name):
    val = breakdown.get(name, 0.0)
    if isinstance(val, dict):
        val = val.get("value", val.get("score", 0.0))
    try:
        return float(val)
    except Exception:
        return 0.0


records = []  # list of (5-vec, action)
n_total = 500
n_errors = 0

for i in range(n_total):
    trust = round(random.uniform(0.1, 1.0), 2)
    conflict = round(random.uniform(0.0, 0.9), 2)
    if trust + conflict > 1.0:
        conflict = round(1.0 - trust, 2)
    age = round(random.uniform(0, 100), 1)
    downstream = random.randint(1, 20)
    mtype = random.choice(MEMORY_TYPES)
    payload = {
        "memory_state": [{
            "id": f"bm_a_{i}",
            "content": f"Boundary probe {i}",
            "type": mtype,
            "timestamp_age_days": age,
            "source_trust": trust,
            "source_conflict": conflict,
            "downstream_count": downstream,
        }],
        "action_type": random.choice(
            ["informational", "reversible", "irreversible", "destructive"]
        ),
        "domain": random.choice(
            ["general", "fintech", "medical", "legal", "coding", "customer_support"]
        ),
    }
    r = client.post("/v1/preflight", headers=AUTH, json=payload)
    if r.status_code != 200:
        n_errors += 1
        continue
    data = r.json()
    action = data.get("recommended_action", "")
    breakdown = data.get("component_breakdown", {}) or {}
    vec = [extract_component(breakdown, c) for c in COMPONENT_NAMES]
    records.append((vec, action))
    if (i + 1) % 100 == 0:
        print(f"  progress: {i + 1}/{n_total}  (errors so far: {n_errors})")

print(f"  done. successful={len(records)}  errors={n_errors}")

from collections import Counter
action_counts = Counter(a for _, a in records)
print(f"  action distribution: {dict(action_counts)}")


def vec_mean(vectors):
    n = len(vectors)
    if n == 0:
        return [0.0] * 5
    return [sum(v[i] for v in vectors) / n for i in range(5)]


def vec_sub(a, b):
    return [a[i] - b[i] for i in range(5)]


def vec_norm(v):
    return math.sqrt(sum(x * x for x in v))


def vec_scale(v, s):
    return [x * s for x in v]


def dot(a, b):
    return sum(a[i] * b[i] for i in range(5))


def fit_boundary(pos_vecs, neg_vecs, pos_label):
    """Mean-difference hyperplane: normal = mean_pos - mean_neg, threshold = midpoint projection.
    Returns (weights dict, threshold, accuracy) on full records labeled by membership in pos set.
    Predicts pos_label when dot(normal, x) > threshold.
    """
    if len(pos_vecs) < 2 or len(neg_vecs) < 2:
        return (
            {l: 0.0 for l in AXIS_LABELS},
            0.0,
            0.0,
        )
    mean_pos = vec_mean(pos_vecs)
    mean_neg = vec_mean(neg_vecs)
    normal = vec_sub(mean_pos, mean_neg)
    nl = vec_norm(normal)
    if nl < 1e-10:
        return ({l: 0.0 for l in AXIS_LABELS}, 0.0, 0.0)
    normal = vec_scale(normal, 1.0 / nl)
    mid = [(mean_pos[i] + mean_neg[i]) / 2.0 for i in range(5)]
    threshold = dot(normal, mid)
    return normal, threshold


def accuracy_for(normal, threshold, records, is_pos_fn):
    correct = 0
    for vec, action in records:
        predicted_pos = dot(normal, vec) > threshold
        actual_pos = is_pos_fn(action)
        if predicted_pos == actual_pos:
            correct += 1
    return correct / len(records) if records else 0.0


# --- Boundary 1: USE_MEMORY (negative) vs not-USE_MEMORY (positive) ---
# Pos = "not USE_MEMORY" (WARN+ASK_USER+BLOCK). We want: w dot x > theta => not USE_MEMORY
print("\n  Boundary 1: USE_MEMORY vs (WARN+ASK_USER+BLOCK)")
pos_1 = [v for v, a in records if a != "USE_MEMORY"]
neg_1 = [v for v, a in records if a == "USE_MEMORY"]
print(f"    non-USE_MEMORY: {len(pos_1)}  USE_MEMORY: {len(neg_1)}")
normal_1, theta_1 = fit_boundary(pos_1, neg_1, "not_use_memory")
acc_1 = accuracy_for(normal_1, theta_1, records, lambda a: a != "USE_MEMORY")
weights_1 = {AXIS_LABELS[i]: round(float(normal_1[i]), 6) for i in range(5)}
print(f"    weights: {weights_1}")
print(f"    threshold: {theta_1:.6f}  accuracy: {acc_1:.4f}")

# --- Boundary 2: (USE_MEMORY+WARN) vs (ASK_USER+BLOCK) ---
# Pos = ASK_USER or BLOCK. Predict w dot x > theta => ASK_USER/BLOCK
print("\n  Boundary 2: (USE_MEMORY+WARN) vs (ASK_USER+BLOCK)")
pos_2 = [v for v, a in records if a in ("ASK_USER", "BLOCK")]
neg_2 = [v for v, a in records if a in ("USE_MEMORY", "WARN")]
print(f"    ASK_USER/BLOCK: {len(pos_2)}  USE_MEMORY/WARN: {len(neg_2)}")
normal_2, theta_2 = fit_boundary(pos_2, neg_2, "ask_or_block")
acc_2 = accuracy_for(
    normal_2, theta_2, records, lambda a: a in ("ASK_USER", "BLOCK")
)
weights_2 = {AXIS_LABELS[i]: round(float(normal_2[i]), 6) for i in range(5)}
print(f"    weights: {weights_2}")
print(f"    threshold: {theta_2:.6f}  accuracy: {acc_2:.4f}")

# --- Boundary 3: (known) BLOCK vs not-BLOCK from batch1 ---
block_boundary = {
    "weights": {
        "risk": 0.24,
        "decay": 0.58,
        "trust": 0.65,
        "corruption": 0.43,
        "belief": 0.0,
    },
    "threshold": 73.5,
    "accuracy": 0.75,
    "source": "research/results/ten_findings_batch1.json",
}

# If batch1 file present, prefer its precise numbers while keeping rounded public eq in 'equations'.
if os.path.exists(BATCH1_PATH):
    try:
        with open(BATCH1_PATH) as f:
            batch1 = json.load(f)
        db = batch1.get("decision_boundary", {})
        if db:
            block_boundary = {
                "weights": {
                    k: round(float(v), 6)
                    for k, v in db.get("weights", {}).items()
                },
                "threshold": round(float(db.get("threshold", 73.5)), 6),
                "accuracy": round(float(db.get("accuracy", 0.75)), 4),
                "source": "research/results/ten_findings_batch1.json",
                "n_samples": db.get("n_samples"),
                "n_block": db.get("n_block"),
                "n_non_block": db.get("n_non_block"),
            }
    except Exception as e:
        print(f"  batch1 load fallback: {e}")


def equation_string(weights_dict, threshold, rhs):
    order = ["risk", "decay", "trust", "corruption", "belief"]
    parts = []
    for k in order:
        w = weights_dict.get(k, 0.0)
        parts.append(f"{w:+.4f}*{k.capitalize()}")
    return f"{' '.join(parts)} > {threshold:.4f}  =>  {rhs}"


eq1 = equation_string(weights_1, theta_1, "not USE_MEMORY (WARN/ASK_USER/BLOCK)")
eq2 = equation_string(weights_2, theta_2, "ASK_USER or BLOCK")
eq3 = equation_string(block_boundary["weights"], block_boundary["threshold"], "BLOCK")

print("\n  --- Equations ---")
print(f"    USE_MEMORY -> WARN:   {eq1}")
print(f"    WARN -> ASK_USER:     {eq2}")
print(f"    ASK_USER -> BLOCK:    {eq3}")

decision_boundaries_result = {
    "use_memory_vs_other": {
        "weights": weights_1,
        "threshold": round(float(theta_1), 6),
        "accuracy": round(float(acc_1), 4),
        "n_use_memory": len(neg_1),
        "n_other": len(pos_1),
        "rule": "dot(w,x) > theta => not USE_MEMORY",
    },
    "ask_or_block_vs_other": {
        "weights": weights_2,
        "threshold": round(float(theta_2), 6),
        "accuracy": round(float(acc_2), 4),
        "n_ask_or_block": len(pos_2),
        "n_other": len(neg_2),
        "rule": "dot(w,x) > theta => ASK_USER or BLOCK",
    },
    "block_vs_other": block_boundary,
    "equations": [
        f"USE_MEMORY -> WARN: {eq1}",
        f"WARN -> ASK_USER: {eq2}",
        f"ASK_USER -> BLOCK: {eq3}",
    ],
    "n_samples": len(records),
    "n_errors": n_errors,
    "action_distribution": dict(action_counts),
}


# ------------------------------------------------------------------
# MERGE + SAVE
# ------------------------------------------------------------------
existing = {}
if os.path.exists(RESULTS_PATH):
    try:
        with open(RESULTS_PATH) as f:
            existing = json.load(f)
        print(f"\n  Loaded existing {RESULTS_PATH} with keys: {list(existing.keys())}")
    except Exception as e:
        print(f"\n  existing results unreadable, starting fresh: {e}")
        existing = {}

existing["expected_savings"] = expected_savings_result
existing["decision_boundaries"] = decision_boundaries_result

os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
with open(RESULTS_PATH, "w") as f:
    json.dump(existing, f, indent=2, sort_keys=True)

print(f"\n  Wrote merged results to {RESULTS_PATH}")
print("  Top-level keys:", list(existing.keys()))
