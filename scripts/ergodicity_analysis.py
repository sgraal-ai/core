"""Ergodicity analysis for Sgraal preflight scoring.

Tests whether AI memory systems are ergodic across agent populations.
If not, per-agent (not population-level) thresholds are required.

Usage:
    python3 scripts/ergodicity_analysis.py
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

# Deterministic seed for reproducibility
random.seed(42)

N_AGENTS_LOW = 15
N_AGENTS_MED = 20
N_AGENTS_HIGH = 15
N_AGENTS = N_AGENTS_LOW + N_AGENTS_MED + N_AGENTS_HIGH
CALLS_PER_AGENT = 30

# Diverse content pool — avoids triggering the consensus_collapse detector,
# which flags repeated templated strings as "redundant summarization" and
# forces omega = 100 via post-reconciliation BLOCK.
CONTENT_POOL = [
    "user selected dark theme in settings",
    "api key rotation scheduled for next tuesday",
    "last backup completed at 03:14 UTC",
    "preferred language is english",
    "billing address located in berlin",
    "open support ticket 4512 about login flow",
    "weather service returned 17 celsius at noon",
    "database connection pool size is 20",
    "feature flag checkout_v2 enabled",
    "calendar sync with outlook configured",
    "slack workspace id ends in xyz42",
    "github repo main branch protected",
    "mobile push notifications disabled",
    "default timezone is europe madrid",
    "recent purchase order id 88123",
    "shipping carrier dhl for orders over 50",
    "vpn endpoint located frankfurt",
    "monthly active users last week 1432",
    "discount code summer25 expires june 30",
    "maintenance window scheduled sunday 2am",
    "invoice 77321 issued to acme corp",
    "sso provider okta group engineers",
    "redis cache hit ratio 92 percent",
    "new hire onboarding doc version 3",
    "quarterly review meeting on friday",
    "privacy policy update effective january",
    "incident postmortem 2025 0412 published",
    "data retention window 365 days",
    "third party vendor list audited monthly",
    "oncall rotation handoff at 9am",
]


def build_personality(agent_idx: int):
    """Return (class_label, age_range, trust_range, conflict_range)."""
    if agent_idx < N_AGENTS_LOW:
        return ("low", (1.0, 5.0), (0.85, 0.95), (0.05, 0.15))
    if agent_idx < N_AGENTS_LOW + N_AGENTS_MED:
        return ("medium", (5.0, 20.0), (0.60, 0.85), (0.10, 0.30))
    return ("high", (20.0, 60.0), (0.30, 0.60), (0.30, 0.60))


def sample_memory_state(rng: random.Random, personality, agent_idx: int, call_idx: int, n_entries=5):
    """Sample a memory_state list for one call, respecting personality bounds.

    Uses diverse content strings from CONTENT_POOL to avoid tripping the
    consensus_collapse detector (which flags repeated templates as
    redundant summarization and forces omega = 100).
    """
    _, age_range, trust_range, conflict_range = personality
    types = ["episodic", "semantic", "preference", "tool_state", "shared_workflow"]
    sampled_contents = rng.sample(CONTENT_POOL, n_entries)
    entries = []
    for i, content in enumerate(sampled_contents):
        age = rng.uniform(*age_range)
        trust = rng.uniform(*trust_range)
        conflict = rng.uniform(*conflict_range)
        entries.append(
            {
                "id": f"a{agent_idx}_c{call_idx}_m{i}",
                "content": content,
                "type": rng.choice(types),
                "timestamp_age_days": round(age, 2),
                "source_trust": round(trust, 3),
                "source_conflict": round(conflict, 3),
                "downstream_count": rng.randint(1, 5),
                "r_belief": round(rng.uniform(0.4, 0.9), 3),
            }
        )
    return entries


def run_preflight(agent_id: str, memory_state: list, domain: str, action_type: str):
    payload = {
        "agent_id": agent_id,
        "memory_state": memory_state,
        "action_type": action_type,
        "domain": domain,
        "dry_run": True,
    }
    r = client.post("/v1/preflight", json=payload, headers=AUTH)
    if r.status_code != 200:
        raise RuntimeError(f"preflight failed: {r.status_code} {r.text[:200]}")
    return r.json()


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def stdev(xs):
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def variance(xs):
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def ks_2samp(x, y):
    """Two-sample Kolmogorov-Smirnov test (manual implementation)."""
    x = sorted(x)
    y = sorted(y)
    nx, ny = len(x), len(y)
    data = sorted(set(x + y))
    cdfx = [sum(1 for v in x if v <= d) / nx for d in data]
    cdfy = [sum(1 for v in y if v <= d) / ny for d in data]
    ks_stat = max(abs(cx - cy) for cx, cy in zip(cdfx, cdfy))
    n_eff = (nx * ny) / (nx + ny)
    kappa = ks_stat * math.sqrt(n_eff)
    p_value = 2 * math.exp(-2 * kappa * kappa) if kappa > 0.1 else 1.0
    return ks_stat, min(1.0, p_value)


def main():
    print(f"[ergodicity] generating {N_AGENTS} agents x {CALLS_PER_AGENT} calls = {N_AGENTS * CALLS_PER_AGENT} calls")

    # omega_matrix[a][t] — omega score of agent a at call t
    omega_matrix = [[0.0] * CALLS_PER_AGENT for _ in range(N_AGENTS)]
    agent_classes = []

    rng_pool = [random.Random(1000 + i) for i in range(N_AGENTS)]

    for a in range(N_AGENTS):
        personality = build_personality(a)
        agent_classes.append(personality[0])
        agent_id = f"agent_{personality[0]}_{a:02d}"
        domain_cycle = ["general", "customer_support", "coding"]
        action_cycle = ["reversible", "informational"]
        for t in range(CALLS_PER_AGENT):
            mem = sample_memory_state(rng_pool[a], personality, a, t, n_entries=5)
            domain = domain_cycle[t % len(domain_cycle)]
            action_type = action_cycle[t % len(action_cycle)]
            try:
                resp = run_preflight(agent_id, mem, domain, action_type)
                omega = float(resp.get("omega_mem_final", 0.0))
            except Exception as e:
                print(f"  agent {a} call {t} failed: {e}")
                omega = float("nan")
            omega_matrix[a][t] = omega
        if (a + 1) % 10 == 0:
            print(f"  [{a + 1}/{N_AGENTS}] agents done")

    # Drop any NaN rows (shouldn't happen, but be defensive)
    clean_matrix = []
    clean_classes = []
    for a in range(N_AGENTS):
        row = omega_matrix[a]
        if any(math.isnan(v) for v in row):
            print(f"  dropping agent {a} due to NaN")
            continue
        clean_matrix.append(row)
        clean_classes.append(agent_classes[a])

    n_agents_clean = len(clean_matrix)

    # Per-agent time averages
    per_agent_time_avgs = [mean(row) for row in clean_matrix]
    per_agent_time_stds = [stdev(row) for row in clean_matrix]

    # Ensemble averages per time step
    ensemble_avg_per_step = []
    for t in range(CALLS_PER_AGENT):
        col = [clean_matrix[a][t] for a in range(n_agents_clean)]
        ensemble_avg_per_step.append(mean(col))

    ensemble_mean = mean(ensemble_avg_per_step)
    ensemble_std = stdev(ensemble_avg_per_step)

    # Ergodicity tests
    ks_stat, ks_p = ks_2samp(per_agent_time_avgs, ensemble_avg_per_step)
    var_agent_time = variance(per_agent_time_avgs)
    var_ensemble_per_step = variance(ensemble_avg_per_step)
    variance_ratio = var_agent_time / var_ensemble_per_step if var_ensemble_per_step > 1e-9 else float("inf")

    ergodic = (ks_stat < 0.2) and (variance_ratio < 2.0)

    above = sum(1 for v in per_agent_time_avgs if v > ensemble_mean + 10)
    below = sum(1 for v in per_agent_time_avgs if v < ensemble_mean - 10)
    within = n_agents_clean - above - below

    recommendation = "population_thresholds_valid" if ergodic else "per_agent_thresholds_recommended"

    if ergodic:
        interpretation = (
            "Per-agent time averages cluster tightly around the ensemble mean "
            f"(KS={ks_stat:.3f}, variance ratio={variance_ratio:.2f}). "
            "Population-level thresholds are statistically justified."
        )
    else:
        interpretation = (
            f"Per-agent time averages diverge systematically from the ensemble mean "
            f"(KS={ks_stat:.3f}, variance ratio={variance_ratio:.2f}). "
            f"{above} agents consistently score >10 points above ensemble mean and "
            f"{below} score >10 points below. A single population-wide BLOCK threshold "
            "will be wrong for a significant fraction of agents. Per-agent calibrated "
            "thresholds (or class-level thresholds by personality) are required."
        )

    # Class-level breakdown (low/medium/high)
    class_stats = {}
    for cls in ("low", "medium", "high"):
        idxs = [i for i, c in enumerate(clean_classes) if c == cls]
        vals = [per_agent_time_avgs[i] for i in idxs]
        if vals:
            class_stats[cls] = {
                "n_agents": len(vals),
                "mean_time_avg": round(mean(vals), 3),
                "std_time_avg": round(stdev(vals), 3),
                "min": round(min(vals), 3),
                "max": round(max(vals), 3),
            }

    result = {
        "data_source": "synthetic_personality_simulation",
        "n_agents": n_agents_clean,
        "calls_per_agent": CALLS_PER_AGENT,
        "n_total_observations": n_agents_clean * CALLS_PER_AGENT,
        "ensemble_mean": round(ensemble_mean, 4),
        "ensemble_std": round(ensemble_std, 4),
        "per_agent_time_averages": {
            "mean": round(mean(per_agent_time_avgs), 4),
            "std": round(stdev(per_agent_time_avgs), 4),
            "min": round(min(per_agent_time_avgs), 4),
            "max": round(max(per_agent_time_avgs), 4),
        },
        "per_agent_time_stds": {
            "mean": round(mean(per_agent_time_stds), 4),
            "min": round(min(per_agent_time_stds), 4),
            "max": round(max(per_agent_time_stds), 4),
        },
        "class_breakdown": class_stats,
        "ergodicity_tests": {
            "ks_statistic": round(ks_stat, 4),
            "ks_pvalue": round(ks_p, 6),
            "variance_ratio": round(variance_ratio, 4),
            "var_per_agent_time_avgs": round(var_agent_time, 4),
            "var_ensemble_per_step": round(var_ensemble_per_step, 4),
            "ergodic": bool(ergodic),
        },
        "agents_above_mean_plus_10": above,
        "agents_below_mean_minus_10": below,
        "agents_within_10_of_mean": within,
        "recommendation": recommendation,
        "interpretation": interpretation,
    }

    out_path = "/Users/zsobrakpeter/core/research/results/ergodicity_analysis.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"[ergodicity] wrote {out_path}")

    # Markdown section
    md = build_markdown(result)
    md_path = "/Users/zsobrakpeter/core/research/results/ergodicity_section.md"
    with open(md_path, "w") as f:
        f.write(md)
    print(f"[ergodicity] wrote {md_path}")

    # Console summary
    print("\n=== Ergodicity Summary ===")
    print(f"  n_agents:                 {n_agents_clean}")
    print(f"  calls/agent:              {CALLS_PER_AGENT}")
    print(f"  ensemble_mean:            {ensemble_mean:.3f}")
    print(f"  per-agent time avg range: [{min(per_agent_time_avgs):.2f}, {max(per_agent_time_avgs):.2f}]")
    print(f"  KS statistic:             {ks_stat:.4f}  (p={ks_p:.4f})")
    print(f"  variance ratio:           {variance_ratio:.4f}")
    print(f"  ergodic?                  {ergodic}")
    print(f"  above +10:                {above}")
    print(f"  below -10:                {below}")
    print(f"  within ±10:               {within}")
    print(f"  recommendation:           {recommendation}")


def build_markdown(r: dict) -> str:
    tests = r["ergodicity_tests"]
    pa = r["per_agent_time_averages"]
    cls = r.get("class_breakdown", {})
    ergodic = tests["ergodic"]
    verdict = "IS" if ergodic else "is NOT"

    lines = []
    lines.append("### 18.1 Ergodicity")
    lines.append("")
    lines.append(
        f"Memory scoring {verdict} ergodic across agent populations. In an ergodic system, "
        "the time average (one agent over many calls) equals the ensemble average "
        "(many agents at one moment). When this equality breaks, a single population-wide "
        "threshold is provably wrong for the agents whose personal distribution sits far "
        "from the crowd."
    )
    lines.append("")
    lines.append(
        f"We simulated {r['n_agents']} agents with distinct risk personalities "
        f"({cls.get('low',{}).get('n_agents',0)} low-risk, {cls.get('medium',{}).get('n_agents',0)} "
        f"medium-risk, {cls.get('high',{}).get('n_agents',0)} high-risk) and ran "
        f"{r['calls_per_agent']} preflight calls per agent ({r['n_total_observations']} observations total)."
    )
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Ensemble mean Ω_MEM | {r['ensemble_mean']} |")
    lines.append(f"| Ensemble std (across time steps) | {r['ensemble_std']} |")
    lines.append(f"| Per-agent time-avg mean | {pa['mean']} |")
    lines.append(f"| Per-agent time-avg std | {pa['std']} |")
    lines.append(f"| Per-agent time-avg range | [{pa['min']}, {pa['max']}] |")
    lines.append(f"| KS statistic (time-avg vs ensemble) | {tests['ks_statistic']} |")
    lines.append(f"| Variance ratio (Var_time / Var_ensemble) | {tests['variance_ratio']} |")
    lines.append(f"| Agents > ensemble + 10 | {r['agents_above_mean_plus_10']} |")
    lines.append(f"| Agents < ensemble − 10 | {r['agents_below_mean_minus_10']} |")
    lines.append(f"| Agents within ±10 of ensemble | {r['agents_within_10_of_mean']} |")
    lines.append(f"| Ergodic? | **{ergodic}** |")
    lines.append("")
    if ergodic:
        lines.append(
            "The scoring engine passes both ergodicity tests "
            f"(KS < 0.20, variance ratio < 2.0). Population-level thresholds (WARN=40, "
            "ASK_USER=60, BLOCK=70) remain statistically defensible for the full fleet."
        )
    else:
        lines.append(
            "**Implication:** population-level thresholds are miscalibrated for roughly "
            f"{r['agents_above_mean_plus_10'] + r['agents_below_mean_minus_10']} of "
            f"{r['n_agents']} agents. Low-risk agents are under-served (BLOCK triggers "
            "earlier than their personal distribution warrants) and high-risk agents are "
            "over-trusted (their personal Ω_MEM baseline sits well above the population "
            "mean, so a global BLOCK=70 misses early-warning regimes). The `thresholds` "
            "field in `/v1/preflight` and per-agent calibration via the `/v1/calibration/*` "
            "endpoints exist precisely to address this — ergodicity violation is the "
            "formal justification."
        )
    lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
