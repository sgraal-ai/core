#!/usr/bin/env python3
"""
TASK 5 — Phase Transition Conjecture

Question: is there a critical omega point where memory collapses suddenly
(first-order transition) rather than gradually?

Method:
  1. Load all benchmark corpus cases via _load_benchmark_corpus()
  2. Run each through /v1/preflight with dry_run=True and
     score_history=[50]*10 (activates temporal modules)
  3. Extract per-case:
       omega_mem_final
       spectral_analysis.fiedler_value (λ₂)
       hmm_regime.state_probability  (when regime == CRITICAL)
       hawkes_intensity.current_lambda
  4. Bin cases by omega into 10-point windows (0-10, 10-20, ..., 90-100)
  5. Compute per-band mean of the 3 signals
  6. Finite-difference derivative across bands → find peak derivative
  7. Classify transition: first-order vs second-order vs gradual
  8. Fit a power-law (log-log slope) as supplementary evidence

All results explicitly labelled "synthetic" where appropriate.
"""
import os
import sys
import json
import math

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")

import numpy as np
from fastapi.testclient import TestClient
from api.main import app, _load_benchmark_corpus

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

OUT_JSON = "/Users/zsobrakpeter/core/research/results/phase_transition_conjecture.json"
OUT_MD = "/Users/zsobrakpeter/core/research/results/phase_transition_section.md"


def _safe_get(d, *path, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p)
        if cur is None:
            return default
    return cur


def run_case(case):
    payload = {
        "memory_state": case.get("memory_state", []),
        "action_type": case.get("action_type", "reversible"),
        "domain": case.get("domain", "general"),
        "dry_run": True,
        "score_history": [50] * 10,
    }
    try:
        r = client.post("/v1/preflight", headers=AUTH, json=payload, timeout=30)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def extract_signals(resp):
    if not resp:
        return None
    omega = resp.get("omega_mem_final")
    if omega is None:
        return None

    fiedler = _safe_get(resp, "spectral_analysis", "fiedler_value")
    # hmm_regime.state_probability is the prob of the *current* state.
    # Weight it as "critical probability" iff current_state==CRITICAL.
    hmm_regime = resp.get("hmm_regime") or {}
    hmm_state = hmm_regime.get("current_state")
    hmm_prob = hmm_regime.get("state_probability")
    hmm_critical = hmm_prob if hmm_state == "CRITICAL" and hmm_prob is not None else 0.0

    hawkes = _safe_get(resp, "hawkes_intensity", "current_lambda")

    return {
        "omega": float(omega),
        "fiedler": float(fiedler) if fiedler is not None else None,
        "hmm_critical": float(hmm_critical),
        "hawkes": float(hawkes) if hawkes is not None else None,
    }


def main():
    cases = _load_benchmark_corpus()
    print(f"Loaded {len(cases)} corpus cases")

    rows = []
    for i, c in enumerate(cases):
        resp = run_case(c)
        sig = extract_signals(resp)
        if sig is not None:
            rows.append(sig)
        if (i + 1) % 50 == 0:
            print(f"  processed {i+1}/{len(cases)}")

    print(f"Extracted signals for {len(rows)} cases")

    # Build omega bands: 0-10, 10-20, ..., 90-100
    bands = []
    for lo in range(0, 100, 10):
        hi = lo + 10
        subset = [r for r in rows if lo <= r["omega"] < hi]
        # Include exact 100 in the last band
        if lo == 90:
            subset = [r for r in rows if lo <= r["omega"] <= 100]

        if not subset:
            bands.append({
                "band": f"{lo}-{hi}",
                "lo": lo,
                "hi": hi,
                "n": 0,
                "mean_omega": None,
                "mean_fiedler": None,
                "mean_hmm_critical": None,
                "mean_hawkes": None,
            })
            continue

        def _mean_of(key):
            vals = [r[key] for r in subset if r.get(key) is not None]
            if not vals:
                return None
            return float(np.mean(vals))

        bands.append({
            "band": f"{lo}-{hi}",
            "lo": lo,
            "hi": hi,
            "n": len(subset),
            "mean_omega": float(np.mean([r["omega"] for r in subset])),
            "mean_fiedler": _mean_of("fiedler"),
            "mean_hmm_critical": _mean_of("hmm_critical"),
            "mean_hawkes": _mean_of("hawkes"),
        })

    # Finite-difference derivatives (only over consecutive bands with data)
    def _deriv(sig_key):
        d = []
        for i in range(len(bands) - 1):
            a = bands[i][sig_key]
            b = bands[i + 1][sig_key]
            if a is None or b is None:
                d.append(None)
            else:
                # center the derivative at the midpoint of the two bands
                x_lo = (bands[i]["lo"] + bands[i]["hi"]) / 2.0
                x_hi = (bands[i + 1]["lo"] + bands[i + 1]["hi"]) / 2.0
                d.append({"at_omega": (x_lo + x_hi) / 2.0, "d": (b - a) / (x_hi - x_lo)})
        return d

    der_fiedler = _deriv("mean_fiedler")
    der_hmm = _deriv("mean_hmm_critical")
    der_hawkes = _deriv("mean_hawkes")

    # Peak-derivative location across the available signals.
    # For fiedler: connectivity *drops* → expect large negative derivative.
    # For hmm_critical and hawkes: expect large positive derivative.
    #
    # Use absolute derivative magnitude, averaged across available signals at
    # each x-point, to localize the transition.
    def _abs(v):
        if v is None:
            return None
        return abs(v["d"])

    scored = []
    for i in range(len(bands) - 1):
        at = bands[i]["hi"]  # boundary location
        contributions = []
        if der_fiedler[i] is not None:
            contributions.append(abs(der_fiedler[i]["d"]))
        if der_hmm[i] is not None:
            contributions.append(abs(der_hmm[i]["d"]))
        if der_hawkes[i] is not None:
            contributions.append(abs(der_hawkes[i]["d"]))
        if contributions:
            scored.append({"at_omega": at, "score": float(np.mean(contributions))})

    if scored:
        peak = max(scored, key=lambda s: s["score"])
        peak_omega = peak["at_omega"]
        peak_score = peak["score"]
    else:
        peak = None
        peak_omega = None
        peak_score = None

    # Transition classification
    # - first_order: peak_score >> mean_score (top 1 band dominates)
    # - second_order: peak/mean ratio modest, broad elevation
    # - gradual: very low peak
    if scored:
        vals = [s["score"] for s in scored]
        mean_score = float(np.mean(vals))
        std_score = float(np.std(vals))
        ratio = (peak_score / mean_score) if mean_score > 1e-9 else float("inf")
        if ratio > 2.5 and peak_score > (mean_score + 2 * std_score):
            transition_type = "first_order"
        elif ratio > 1.5:
            transition_type = "second_order"
        else:
            transition_type = "gradual"
    else:
        mean_score = None
        std_score = None
        ratio = None
        transition_type = "insufficient_data"

    # Power-law fit: abs-derivative-scores vs |omega - peak_omega|
    power_law_exponent = None
    if scored and peak_omega is not None and len(scored) >= 4:
        xs, ys = [], []
        for s in scored:
            dist = abs(s["at_omega"] - peak_omega)
            if dist > 0 and s["score"] > 0:
                xs.append(math.log(dist))
                ys.append(math.log(s["score"]))
        if len(xs) >= 3:
            xs_a = np.array(xs)
            ys_a = np.array(ys)
            # OLS slope
            slope, intercept = np.polyfit(xs_a, ys_a, 1)
            power_law_exponent = float(slope)

    # Interpretation
    if transition_type == "first_order":
        interp = (
            f"A first-order-like discontinuity is observed near omega ~ {peak_omega}. "
            "The combined (λ₂, HMM-critical, Hawkes) signal derivative spikes sharply "
            "at this boundary, indicating that memory system behaviour flips rather "
            "than drifts as omega crosses this point."
        )
    elif transition_type == "second_order":
        interp = (
            f"A second-order-like transition is observed near omega ~ {peak_omega}. "
            "The signals bend steeply but continuously; "
            f"a power-law tail with exponent ~ {power_law_exponent} is consistent with "
            "critical-point-like scaling rather than a hard step."
        )
    elif transition_type == "gradual":
        interp = (
            "No sharp critical point is visible in this corpus. The signals degrade "
            "roughly linearly with omega, suggesting gradual rather than catastrophic "
            "memory collapse within the tested range."
        )
    else:
        interp = "Not enough signal coverage across the omega bands to classify."

    result = {
        "synthetic": True,
        "n_cases_analyzed": len(rows),
        "omega_bands": bands,
        "derivatives": {
            "fiedler_vs_omega": der_fiedler,
            "hmm_critical_vs_omega": der_hmm,
            "hawkes_vs_omega": der_hawkes,
        },
        "combined_abs_derivative_scores": scored,
        "empirical_critical_omega": peak_omega,
        "max_derivative_location": peak_omega,
        "max_derivative_score": peak_score,
        "mean_derivative_score": mean_score,
        "std_derivative_score": std_score,
        "peak_to_mean_ratio": ratio,
        "transition_type": transition_type,
        "power_law_exponent": power_law_exponent,
        "interpretation": interp,
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)

    # Markdown section
    md_lines = []
    md_lines.append("### 19.5 Phase Transition Conjecture")
    md_lines.append("")
    md_lines.append(
        f"We scored {len(rows)} benchmark corpus cases through `/v1/preflight` "
        "(dry-run, `score_history=[50]*10` to activate temporal modules) and "
        "tracked three collapse signals versus `omega_mem_final`: "
        "spectral Fiedler value λ₂, HMM critical-state probability, and "
        "Hawkes intensity λ."
    )
    md_lines.append("")
    md_lines.append("| ω band | n | mean λ₂ | mean HMM-crit | mean Hawkes |")
    md_lines.append("|--------|---|---------|---------------|-------------|")
    for b in bands:
        if b["n"] == 0:
            md_lines.append(f"| {b['band']} | 0 | – | – | – |")
            continue

        def fmt(v):
            return "–" if v is None else f"{v:.4f}"
        md_lines.append(
            f"| {b['band']} | {b['n']} | {fmt(b['mean_fiedler'])} | "
            f"{fmt(b['mean_hmm_critical'])} | {fmt(b['mean_hawkes'])} |"
        )
    md_lines.append("")
    md_lines.append(
        f"**Empirical critical ω (max |Δsignal/Δω|):** "
        f"{peak_omega if peak_omega is not None else 'n/a'}  "
    )
    md_lines.append(f"**Peak-to-mean derivative ratio:** "
                    f"{('%.2f' % ratio) if ratio is not None else 'n/a'}  ")
    md_lines.append(f"**Transition classification:** `{transition_type}`  ")
    md_lines.append(
        f"**Power-law exponent (|ω − ω_c| fit):** "
        f"{('%.3f' % power_law_exponent) if power_law_exponent is not None else 'n/a'}"
    )
    md_lines.append("")
    md_lines.append(interp)
    md_lines.append("")
    md_lines.append(
        "_Synthetic: results are derived from dry-run scoring on the packaged benchmark "
        "corpus and should be corroborated on production decision data before being "
        "used to move action thresholds._"
    )

    with open(OUT_MD, "w") as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"transition_type={transition_type}  empirical_critical_omega={peak_omega}")


if __name__ == "__main__":
    main()
