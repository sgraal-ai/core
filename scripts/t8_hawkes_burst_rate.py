"""
T8 — Hawkes Burst Rate from Corpus

Estimates inter-arrival time between attacks across 1,070 corpus cases
(R1-R10). Real timestamps are not available, so each case is assigned a
synthetic 1-attack/day arrival within its round.  Per-domain arrival
rate λ and 24 h burst probability are reported for Hawkes calibration.
"""

from __future__ import annotations

import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")
sys.path.insert(0, "/Users/zsobrakpeter/core/tests/corpus")

from api.main import _load_benchmark_corpus  # noqa: E402


def _collect_cases() -> list[dict]:
    """Return list of {round, domain, attack_vector, index_in_round}."""
    cases: list[dict] = []

    # Rounds 1-4 + 9 via API helper
    try:
        for i, c in enumerate(_load_benchmark_corpus()):
            cases.append({
                "round": f"R{c.get('round', '?')}",
                "domain": c.get("domain", "general") or "general",
                "attack_vector": c.get("id", "") or f"round{c.get('round')}",
                "source": "load_benchmark_corpus",
            })
    except Exception as e:  # noqa: BLE001
        print(f"[t8] warn: _load_benchmark_corpus failed: {e}")

    # Round 5
    try:
        from round5_consensus_poisoning import CASES as R5
        for c in R5:
            cases.append({
                "round": "R5",
                "domain": c.get("domain", "general") or "general",
                "attack_vector": c.get("case_id", "") or "r5",
                "source": "R5",
            })
    except Exception as e:  # noqa: BLE001
        print(f"[t8] warn: R5 import failed: {e}")

    # Round 6
    try:
        from round6_memory_time_attack import CASES as R6
        for c in R6:
            cases.append({
                "round": "R6",
                "domain": c.get("domain", "general") or "general",
                "attack_vector": c.get("case_id", "") or "r6",
                "source": "R6",
            })
    except Exception as e:  # noqa: BLE001
        print(f"[t8] warn: R6 import failed: {e}")

    # Round 7
    try:
        from round7_identity_drift import CASES as R7
        for c in R7:
            cases.append({
                "round": "R7",
                "domain": c.get("domain", "general") or "general",
                "attack_vector": c.get("case_id", "") or "r7",
                "source": "R7",
            })
    except Exception as e:  # noqa: BLE001
        print(f"[t8] warn: R7 import failed: {e}")

    # Round 8
    try:
        from round8_consensus_collapse import CASES as R8
        for c in R8:
            cases.append({
                "round": "R8",
                "domain": c.get("domain", "general") or "general",
                "attack_vector": c.get("case_id", "") or "r8",
                "source": "R8",
            })
    except Exception as e:  # noqa: BLE001
        print(f"[t8] warn: R8 import failed: {e}")

    # Round 10
    try:
        with open("/Users/zsobrakpeter/core/tests/corpus/round10/round10_corpus.json") as f:
            r10_obj = json.load(f)
        for c in r10_obj.get("cases", []):
            cases.append({
                "round": "R10",
                "domain": c.get("domain", "general") or "general",
                "attack_vector": c.get("attack_vector", "") or "r10",
                "source": "R10",
            })
    except Exception as e:  # noqa: BLE001
        print(f"[t8] warn: R10 import failed: {e}")

    return cases


def _synth_timestamps(cases: list[dict]) -> list[dict]:
    """Assign synthetic day-index timestamps: 1 attack per day per (domain, round)."""
    # Group by (domain, round) and assign incrementing day numbers
    counters: dict[tuple, int] = {}
    enriched = []
    for c in cases:
        key = (c["domain"], c["round"])
        counters[key] = counters.get(key, 0) + 1
        c2 = dict(c)
        c2["day_index"] = counters[key]  # attack #N within (domain, round)
        enriched.append(c2)
    return enriched


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = k - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def main() -> None:
    cases = _collect_cases()
    print(f"[t8] collected {len(cases)} corpus cases")
    cases = _synth_timestamps(cases)

    corpora_analyzed = sorted({c["source"] for c in cases})
    # Group into fleets: (domain, round) — "same fleet same attack family"
    fleets: dict[tuple, list[dict]] = {}
    for c in cases:
        fleets.setdefault((c["domain"], c["round"]), []).append(c)

    # Inter-arrival times within each fleet, in days (day_index diffs, min 1.0)
    inter_arrivals: list[float] = []
    for key, grp in fleets.items():
        grp.sort(key=lambda x: x["day_index"])
        for i in range(1, len(grp)):
            delta = grp[i]["day_index"] - grp[i - 1]["day_index"]
            if delta > 0:
                inter_arrivals.append(float(delta))

    inter_arrivals.sort()
    n_intervals = len(inter_arrivals)
    mean_ia = sum(inter_arrivals) / n_intervals if n_intervals else 0.0
    median_ia = _percentile(inter_arrivals, 0.5)
    p25 = _percentile(inter_arrivals, 0.25)
    p75 = _percentile(inter_arrivals, 0.75)

    # Per-domain arrival rate: attacks per day = count / max_day_index_in_domain
    per_domain: dict[str, float] = {}
    per_domain_counts: dict[str, int] = {}
    per_domain_span: dict[str, float] = {}
    by_domain: dict[str, list[dict]] = {}
    for c in cases:
        by_domain.setdefault(c["domain"], []).append(c)
    for dom, grp in by_domain.items():
        # span = length of window the corpus covers for that domain
        # = max day_index across (domain, round) buckets
        span = max(c["day_index"] for c in grp) or 1
        per_domain[dom] = round(len(grp) / span, 4)
        per_domain_counts[dom] = len(grp)
        per_domain_span[dom] = span

    # Fleet-level arrival rate = total_attacks / max_span_across_fleets
    global_span = max((len(grp) for grp in fleets.values()), default=1)
    lambda_arrival_global = len(cases) / global_span if global_span else 0.0
    expected_ia = 1.0 / lambda_arrival_global if lambda_arrival_global else 0.0

    # Burst probability in 24 h after an attack:
    # P(next inter-arrival ≤ 1 day) under the empirical distribution
    burst_24h = sum(1 for v in inter_arrivals if v <= 1.0) / n_intervals if n_intervals else 0.0

    # Operational implication
    heaviest_dom = max(per_domain.items(), key=lambda kv: kv[1])[0] if per_domain else "n/a"
    implication = (
        f"Across {len(cases)} cases and {len(fleets)} (domain, round) fleets, "
        f"mean synthetic inter-arrival is {mean_ia:.2f} days, median {median_ia:.2f} days. "
        f"Global arrival intensity λ≈{lambda_arrival_global:.3f} attacks/day per fleet. "
        f"Empirical 24h burst probability = {burst_24h * 100:.1f}%. "
        f"Highest-rate domain: {heaviest_dom} ({per_domain.get(heaviest_dom, 0):.3f} attacks/day). "
        f"Hawkes μ (baseline intensity) should be seeded near {lambda_arrival_global:.3f}; "
        f"self-excitation α should amplify only when multiple attacks arrive within <{median_ia:.0f} days."
    )

    out = {
        "n_corpus_cases": len(cases),
        "corpora_analyzed": corpora_analyzed,
        "n_fleets": len(fleets),
        "n_inter_arrival_samples": n_intervals,
        "per_domain_arrival_rate": per_domain,
        "per_domain_counts": per_domain_counts,
        "per_domain_span_days": per_domain_span,
        "global_lambda_arrival": round(lambda_arrival_global, 4),
        "expected_inter_arrival_days": round(expected_ia, 4),
        "mean_inter_arrival_days": round(mean_ia, 4),
        "median_inter_arrival_days": round(median_ia, 4),
        "p25_inter_arrival_days": round(p25, 4),
        "p75_inter_arrival_days": round(p75, 4),
        "burst_probability_24h": round(burst_24h, 4),
        "operational_implication": implication,
        "methodology": (
            "Synthetic 1-attack-per-day arrivals within each (domain, round) fleet. "
            "Real corpus cases lack true timestamps — this assigns sequential day "
            "indices per fleet, giving a normalised inter-arrival distribution."
        ),
    }

    out_path = "/Users/zsobrakpeter/core/research/results/hawkes_burst_rate.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    print(f"[t8] {len(cases)} cases, {len(fleets)} fleets, {n_intervals} IA samples")
    print(f"[t8] λ_global={lambda_arrival_global:.3f}/day, mean_IA={mean_ia:.2f}d, burst24h={burst_24h:.2%}")
    print(f"[t8] domains: {per_domain}")
    print(f"[t8] wrote {out_path}")


if __name__ == "__main__":
    main()
