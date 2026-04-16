"""B4 — RL Q-table Policy Visualization / Analysis.

Inspects the in-process RL Q-table for each domain, reports convergence,
mean Q per action, and a qualitative policy character.

Because the Q-table lives in memory (no Redis persistence by default),
this snapshot reflects whatever training has occurred in the current
process. On a freshly-booted API that has seen no /v1/outcome calls we
will observe "cold_start" across the board — that is itself a finding.

To produce a more interesting snapshot for analysis, we also drive a
small number of synthetic outcomes through /v1/outcome for each domain
before reading the table. This mimics what the live system would look
like after modest traffic.
"""
from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402
from scoring_engine.rl_policy import (  # noqa: E402
    ACTIONS,
    DOMAINS,
    _discretize,
    _q_table,
    _state_key,
)

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}
RESULTS_PATH = Path("/Users/zsobrakpeter/core/research/results/rl_policy_analysis.json")

DOMAINS_OF_INTEREST = ["general", "fintech", "medical", "coding", "legal", "customer_support"]
TOTAL_CELLS_PER_DOMAIN = 256 * len(ACTIONS)  # 4^4 states × 4 actions = 1024

RNG = random.Random(20260416)


def _make_state(stress: float) -> list[dict]:
    age = 1.0 + stress * 100.0
    trust = max(0.1, 0.95 - stress * 0.7)
    conflict = min(0.9, stress * 0.8)
    return [
        {
            "id": f"e{i}",
            "content": f"entry {i}",
            "type": "semantic",
            "timestamp_age_days": age + i,
            "source_trust": max(0.05, trust - i * 0.05),
            "source_conflict": min(0.95, conflict + i * 0.03),
            "downstream_count": 1 + i,
        }
        for i in range(3)
    ]


def warm_qtable(episodes_per_domain: int = 30) -> None:
    """Drive a few preflight/outcome cycles per domain to populate Q-values."""
    for dom in DOMAINS_OF_INTEREST:
        for _ in range(episodes_per_domain):
            stress = RNG.uniform(0.05, 0.95)
            state = _make_state(stress)
            pf = client.post(
                "/v1/preflight",
                headers=AUTH,
                json={"memory_state": state, "action_type": "reversible", "domain": dom},
            )
            if pf.status_code >= 400:
                continue
            body = pf.json()
            oid = body.get("outcome_id")
            if not oid:
                continue
            # Outcome probabilistically correlated with omega.
            omega = float(body.get("omega_mem_final", 50.0))
            p_succ = max(0.05, min(0.95, 1.0 - (omega - 46.0) * 0.015))
            status = "success" if RNG.random() < p_succ else "failure"
            client.post(
                "/v1/outcome",
                headers=AUTH,
                json={"outcome_id": oid, "status": status, "failure_components": []},
            )


def analyze_domain(domain: str) -> dict:
    tables = _q_table._tables.get(domain, {})
    populated_states = len(tables)
    # Count non-zero cells (state, action).
    populated_cells = 0
    per_action_sums = [0.0, 0.0, 0.0, 0.0]
    per_action_counts = [0, 0, 0, 0]
    for state_key, q_values in tables.items():
        for i, q in enumerate(q_values):
            per_action_sums[i] += q
            per_action_counts[i] += 1
            if abs(q) > 1e-9:
                populated_cells += 1

    mean_q_per_action = {}
    for i, name in enumerate(ACTIONS):
        n = per_action_counts[i]
        mean_q_per_action[name] = round(per_action_sums[i] / n, 4) if n else 0.0

    convergence_ratio = populated_cells / TOTAL_CELLS_PER_DOMAIN
    if convergence_ratio < 0.05:
        convergence = "cold_start"
    elif convergence_ratio < 0.25:
        convergence = "warming"
    else:
        convergence = "converged"

    # Policy character
    if populated_cells == 0:
        character = "insufficient_data"
    else:
        block_q = mean_q_per_action["BLOCK"]
        use_q = mean_q_per_action["USE_MEMORY"]
        diff = block_q - use_q
        if abs(diff) < 0.05:
            character = "balanced"
        elif diff > 0:
            character = "conservative"
        else:
            character = "permissive"

    return {
        "populated_states": populated_states,
        "populated_cells": populated_cells,
        "total_cells": TOTAL_CELLS_PER_DOMAIN,
        "convergence_ratio": round(convergence_ratio, 4),
        "convergence": convergence,
        "episodes": _q_table.get_episodes(domain),
        "mean_q_per_action": mean_q_per_action,
        "policy_character": character,
    }


def run() -> dict:
    # First snapshot: cold Q-table as seen at process start.
    cold_snapshot = {d: analyze_domain(d) for d in DOMAINS_OF_INTEREST}

    # Warm it up with synthetic traffic.
    warm_qtable(episodes_per_domain=30)

    warm_snapshot = {d: analyze_domain(d) for d in DOMAINS_OF_INTEREST}

    # Overall convergence: take the most advanced state across domains.
    order = {"cold_start": 0, "warming": 1, "converged": 2}
    best = max(warm_snapshot.values(), key=lambda r: order[r["convergence"]])
    overall = best["convergence"]

    if overall == "cold_start":
        recommendation = (
            "Q-table is cold — RL adjustments will defer to the base scoring engine. "
            "Drive additional /v1/outcome calls to accumulate learning episodes."
        )
    elif overall == "warming":
        recommendation = (
            "Q-table is warming. Per-domain policies are forming but confidence is low. "
            "Monitor policy_character drift before trusting rl_adjusted_action overrides."
        )
    else:
        recommendation = (
            "Q-table converged enough to trust RL adjustments for this domain. "
            "Review policy_character: persistent 'permissive' on high-criticality domains "
            "(medical/fintech/legal) warrants audit."
        )

    return {
        "extraction_method": "direct_q_table_access",
        "total_state_action_pairs": TOTAL_CELLS_PER_DOMAIN,
        "actions": ACTIONS,
        "per_domain": warm_snapshot,
        "per_domain_cold_snapshot": cold_snapshot,
        "overall_convergence": overall,
        "recommendation": recommendation,
        "warming_episodes_per_domain": 30,
        "note": "Q-table is in-memory; snapshot reflects the current process only.",
    }


if __name__ == "__main__":
    result = run()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"\nSaved: {RESULTS_PATH}")
