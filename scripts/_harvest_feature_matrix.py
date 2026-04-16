#!/usr/bin/env python3
"""
Shared harvester for 132-feature matrix from /v1/preflight.

Mirrors the feature spec used in scripts/fim_83x83.py so Tasks 8, 9, and 11
can operate on the same matrix definition.

Returns:
    X (np.ndarray, shape [n_cases, n_features])
    feature_names (list[str])
    meta dict with per-case metadata (omega_mem_final, recommended_action, etc.)
"""

from __future__ import annotations

import os
import sys
import math
import json
from typing import Optional

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")

import numpy as np
from fastapi.testclient import TestClient

from api.main import app, _load_benchmark_corpus

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


# Module field spec (copied from fim_83x83.py)
MODULE_FIELDS = [
    ("component_breakdown", ["s_freshness", "s_drift", "s_provenance", "s_propagation",
                              "r_recall", "r_encode", "s_interference", "s_recovery",
                              "r_belief", "s_relevance"]),
    ("mttr_analysis", ["mttr_estimate", "mttr_p95", "recovery_probability", "weibull_k", "weibull_lambda"]),
    ("mdp_recommendation", ["expected_value", "confidence"]),
    ("ctl_verification", ["verification_time_ms"]),
    ("lyapunov_exponent", ["lambda_estimate", "divergence_rate"]),
    ("banach_contraction", ["k_estimate", "convergence_steps", "fixed_point_estimate"]),
    ("hotelling_t2", ["t2_statistic", "ucl"]),
    ("hmm_regime", ["state_probability", "regime_duration"]),
    ("bocpd", ["p_changepoint", "current_run_length"]),
    ("rmt_analysis", ["signal_ratio"]),
    ("consistency_analysis", ["h1_rank", "consistency_score"]),
    ("spectral_analysis", ["fiedler_value", "spectral_gap", "cheeger_bound", "mixing_time_estimate"]),
    ("consolidation", ["mean_consolidation"]),
    ("jump_diffusion", ["jump_rate_lambda", "diffusion_sigma"]),
    ("ornstein_uhlenbeck", ["half_life", "current_deviation"]),
    ("free_energy", ["F", "elbo", "kl_divergence", "reconstruction", "surprise"]),
    ("levy_flight", ["alpha", "scale", "extreme_event_probability"]),
    ("rate_distortion", ["total_rate", "total_distortion", "compression_ratio"]),
    ("unified_loss", ["L_v4"]),
    ("policy_gradient", ["advantage", "temperature", "policy_entropy"]),
    ("info_thermodynamics", ["transfer_entropy", "landauer_bound", "information_temperature", "entropy_production"]),
    ("mahalanobis_analysis", ["mean_distance", "covariance_condition"]),
    ("page_hinkley", ["ph_statistic", "change_magnitude", "running_mean"]),
    ("provenance_entropy", ["mean_entropy"]),
    ("subjective_logic", ["fused_opinion"]),
    ("frechet_distance", ["fd_score", "mean_shift"]),
    ("mutual_information", ["mi_score", "nmi_score", "information_loss"]),
    ("fisher_rao", ["condition_number"]),
    ("copula_analysis", ["rho", "joint_risk"]),
    ("mewma", ["T2_stat", "control_limit"]),
    ("drift_details", ["kl_divergence", "wasserstein", "jsd", "alpha_divergence", "ensemble_score"]),
    ("calibration", ["brier_score", "log_loss", "meta_score"]),
    ("hawkes_intensity", ["current_lambda", "baseline_mu"]),
    ("ricci_curvature", ["mean_curvature"]),
    ("koopman", ["eigenvalue", "prediction_5"]),
    ("ergodicity", ["delta"]),
    ("extended_freshness", ["ensemble_freshness"]),
    ("cox_hazard", ["hazard_score"]),
    ("arrhenius", ["thermal_rate"]),
    ("owa_provenance", ["orness"]),
    ("poisson_recall", ["lambda"]),
    ("roc_monitoring", ["auc"]),
    ("particle_filter", ["state_estimate", "uncertainty", "effective_sample_size"]),
    ("dirichlet_process", ["n_clusters", "concentration"]),
    ("pctl_verification", ["probability"]),
    ("dual_process_auq", ["system1_confidence", "system2_confidence"]),
    ("security_transfer_entropy", ["leakage_score"]),
    ("simulated_annealing", ["current_temperature", "best_loss"]),
    ("lqr_control", ["optimal_control", "state_deviation", "control_effort"]),
    ("persistence_landscape", ["landscape_norm"]),
    ("topological_entropy", ["entropy_estimate"]),
    ("frontdoor_effect", ["effect_estimate"]),
    ("expected_utility", ["EU"]),
    ("cvar_risk", ["var", "cvar"]),
]

TOP_LEVEL_SCALARS = [
    "omega_mem_final", "assurance_score", "gsv",
    "naturalness_score", "attack_surface_score", "collapse_ratio",
]


def _coerce_float(val) -> float:
    try:
        if val is None:
            return 0.0
        if isinstance(val, bool):
            return float(val)
        if isinstance(val, (int, float)):
            if math.isnan(val) or math.isinf(val):
                return 0.0
            return float(val)
        return 0.0
    except Exception:
        return 0.0


def extract_vector(resp: dict) -> dict:
    """Harvest ~132 numeric fields from a preflight response. Missing -> 0.0."""
    vec: dict = {}

    for module_key, fields in MODULE_FIELDS:
        mod = resp.get(module_key)
        if not isinstance(mod, dict):
            for f in fields:
                vec[f"{module_key}.{f}"] = 0.0
            continue
        for f in fields:
            vec[f"{module_key}.{f}"] = _coerce_float(mod.get(f))

    for s in TOP_LEVEL_SCALARS:
        vec[f"top.{s}"] = _coerce_float(resp.get(s))

    sv = resp.get("shapley_values")
    if isinstance(sv, dict):
        vals = [_coerce_float(v) for v in sv.values()]
        vec["shapley_values.count"] = float(len(vals))
        vec["shapley_values.mean"] = float(sum(vals) / len(vals)) if vals else 0.0
    elif isinstance(sv, list):
        vals = [_coerce_float(v) for v in sv]
        vec["shapley_values.count"] = float(len(vals))
        vec["shapley_values.mean"] = float(sum(vals) / len(vals)) if vals else 0.0
    else:
        vec["shapley_values.count"] = 0.0
        vec["shapley_values.mean"] = 0.0

    auth = resp.get("authority_scores")
    if isinstance(auth, list):
        vals = [_coerce_float(v) for v in auth]
        vec["authority_scores.count"] = float(len(vals))
        vec["authority_scores.mean"] = float(sum(vals) / len(vals)) if vals else 0.0
    elif isinstance(auth, dict):
        vals = [_coerce_float(v) for v in auth.values()]
        vec["authority_scores.count"] = float(len(vals))
        vec["authority_scores.mean"] = float(sum(vals) / len(vals)) if vals else 0.0
    else:
        vec["authority_scores.count"] = 0.0
        vec["authority_scores.mean"] = 0.0

    ph = resp.get("persistent_homology")
    if isinstance(ph, dict):
        vec["persistent_homology.betti_0"] = _coerce_float(ph.get("betti_0"))
        vec["persistent_homology.betti_1"] = _coerce_float(ph.get("betti_1"))
    else:
        vec["persistent_homology.betti_0"] = 0.0
        vec["persistent_homology.betti_1"] = 0.0

    sm = resp.get("sparse_merkle")
    if isinstance(sm, dict):
        vec["sparse_merkle.ok"] = _coerce_float(sm.get("verified", sm.get("ok", 0)))
    else:
        vec["sparse_merkle.ok"] = 0.0

    ht = resp.get("homology_torsion")
    if isinstance(ht, dict):
        vec["homology_torsion.detected"] = _coerce_float(
            ht.get("torsion_detected", ht.get("hallucination_risk", 0))
        )
    else:
        vec["homology_torsion.detected"] = 0.0

    gs = resp.get("gumbel_softmax")
    if isinstance(gs, dict):
        vec["gumbel_softmax.entropy"] = _coerce_float(gs.get("entropy", gs.get("temperature", 0)))
    else:
        vec["gumbel_softmax.entropy"] = 0.0

    return vec


def harvest_matrix(cache_path: Optional[str] = None, verbose: bool = True):
    """
    Run the full 449-case benchmark corpus through /v1/preflight and return
    (X, feature_names, meta).

    If `cache_path` is provided and the file exists, load the cached matrix
    instead of re-running the corpus (massive speedup for multiple tasks).
    """
    if cache_path and os.path.exists(cache_path):
        if verbose:
            print(f"Loading cached feature matrix from {cache_path}", flush=True)
        with open(cache_path) as f:
            cached = json.load(f)
        X = np.array(cached["X"], dtype=np.float64)
        feature_names = cached["feature_names"]
        meta = cached["meta"]
        if verbose:
            print(f"  loaded shape: {X.shape}", flush=True)
        return X, feature_names, meta

    if verbose:
        print("Loading benchmark corpus...", flush=True)
    cases = _load_benchmark_corpus()
    if verbose:
        print(f"Loaded {len(cases)} cases", flush=True)

    vectors: list[list[float]] = []
    feature_names: Optional[list[str]] = None
    meta_rows: list[dict] = []
    n_ok = 0
    n_fail = 0

    for i, c in enumerate(cases):
        body = {
            "memory_state": c["memory_state"],
            "action_type": c.get("action_type", "reversible"),
            "domain": c.get("domain", "general"),
            "dry_run": True,
            "score_history": [50.0 + 0.1 * (i % 30), 51.0, 49.0, 52.0, 48.0,
                              53.0, 47.0, 54.0, 46.0, 55.0, 45.0, 56.0],
        }
        try:
            r = client.post("/v1/preflight", json=body, headers=AUTH)
            if r.status_code != 200:
                n_fail += 1
                continue
            resp = r.json()
            vec = extract_vector(resp)
            if feature_names is None:
                feature_names = list(vec.keys())
            row = [vec.get(k, 0.0) for k in feature_names]
            vectors.append(row)
            meta_rows.append({
                "case_idx": int(i),
                "domain": c.get("domain", "general"),
                "action_type": c.get("action_type", "reversible"),
                "omega_mem_final": _coerce_float(resp.get("omega_mem_final")),
                "recommended_action": str(resp.get("recommended_action", "")),
            })
            n_ok += 1
            if verbose and (n_ok % 50) == 0:
                print(f"  processed {n_ok} / {len(cases)}", flush=True)
        except Exception:
            n_fail += 1

    if verbose:
        print(f"Done. ok={n_ok}, fail={n_fail}", flush=True)

    X = np.array(vectors, dtype=np.float64)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    meta = {
        "n_ok": int(n_ok),
        "n_fail": int(n_fail),
        "rows": meta_rows,
    }

    if cache_path:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump({
                "X": X.tolist(),
                "feature_names": feature_names,
                "meta": meta,
            }, f)
        if verbose:
            print(f"Cached feature matrix to {cache_path}", flush=True)

    return X, feature_names, meta


if __name__ == "__main__":
    # Pre-cache when run directly
    cache = "/tmp/sgraal_feature_matrix_cache.json"
    X, feats, meta = harvest_matrix(cache_path=cache)
    print(f"Shape: {X.shape}, n_features: {len(feats)}")
    actions = {}
    for row in meta["rows"]:
        actions[row["recommended_action"]] = actions.get(row["recommended_action"], 0) + 1
    print(f"Action distribution: {actions}")
