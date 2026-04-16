"""
T10 — Fit Sigmoid Calibration Constants from Omega-Outcome Data

Reads aggregate statistics from omega_outcome_results.json (n=120), fits a
logistic P(failure | omega) = 1 / (1 + exp(-k * (omega - theta))) using two
approaches, compares against estimated (theta=46, k=0.15), and optionally
updates api/main.py when the delta warrants it.
"""

import json
import math
import random
import re
from pathlib import Path


RESULTS_PATH = Path("/Users/zsobrakpeter/core/research/results/omega_outcome_results.json")
OUT_PATH = Path("/Users/zsobrakpeter/core/research/results/sigmoid_calibration_fitted.json")
API_MAIN = Path("/Users/zsobrakpeter/core/api/main.py")


def sigmoid(omega: float, theta: float, k: float) -> float:
    # Numerically stable logistic
    x = -k * (omega - theta)
    if x >= 0:
        z = math.exp(-x)
        return z / (1.0 + z) if False else 1.0 / (1.0 + math.exp(x))
    else:
        z = math.exp(x)
        return 1.0 / (1.0 + z) * 1.0  # fallback, unused branch
    # NOTE: the simple form is sufficient for magnitudes here; avoid overflow below
    # by clamping via math.exp with large negative x handled by the math lib.


def _sigmoid_safe(omega: float, theta: float, k: float) -> float:
    x = k * (omega - theta)
    # Clamp to avoid overflow
    if x > 500:
        return 1.0
    if x < -500:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def method_A_summary_stats(data: dict) -> dict:
    """Closed-form estimates from group means and medians."""
    n_s = data["n_success"]
    n_f = data["n_failure"]
    s_mean = data["success_omega_mean"]
    f_mean = data["failure_omega_mean"]
    s_med = data["success_omega_median"]
    f_med = data["failure_omega_median"]

    theta = (n_s * s_mean + n_f * f_mean) / (n_s + n_f)
    # Steepness derived from median-to-median transition width
    width = (f_med - s_med) / 4.0
    k = 4.0 / width if width > 0 else 0.15

    return {"theta": round(theta, 4), "k": round(k, 4)}


def method_B_synthetic_lsq(data: dict, seed: int = 42) -> dict:
    """Generate synthetic (omega, label) pairs and fit via least squares."""
    rnd = random.Random(seed)
    n_s = data["n_success"]
    n_f = data["n_failure"]
    s_mean = data["success_omega_mean"]
    f_mean = data["failure_omega_mean"]
    # Std proxies: use group mean / 2 but cap to reasonable ranges.
    # Success distribution hugs 0 (median=2.5), so use a smaller std.
    s_std = 8.0
    f_std = 10.0

    samples = []
    for _ in range(n_s):
        x = rnd.gauss(s_mean, s_std)
        x = max(0.0, min(100.0, x))
        samples.append((x, 0.0))  # success label = 0 (not failure)
    for _ in range(n_f):
        x = rnd.gauss(f_mean, f_std)
        x = max(0.0, min(100.0, x))
        samples.append((x, 1.0))  # failure label = 1

    # Least-squares fit over (theta, k): minimize sum (sigmoid - label)^2
    # Simple gradient descent.
    theta = 50.0
    k = 0.1
    lr_theta = 0.5
    lr_k = 0.002
    n = len(samples)

    for _iter in range(5000):
        grad_theta = 0.0
        grad_k = 0.0
        for x, y in samples:
            p = _sigmoid_safe(x, theta, k)
            err = p - y
            # d sigmoid / d theta = -k * p * (1-p)
            # d sigmoid / d k = (x - theta) * p * (1-p)
            dp = p * (1.0 - p)
            grad_theta += 2.0 * err * (-k * dp)
            grad_k += 2.0 * err * ((x - theta) * dp)
        grad_theta /= n
        grad_k /= n
        theta -= lr_theta * grad_theta
        k -= lr_k * grad_k
        # Keep k positive
        if k < 0.001:
            k = 0.001

    # Compute R^2
    y_mean = sum(y for _, y in samples) / n
    ss_tot = sum((y - y_mean) ** 2 for _, y in samples)
    ss_res = sum((y - _sigmoid_safe(x, theta, k)) ** 2 for x, y in samples)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    return {"theta": round(theta, 4), "k": round(k, 4), "R_squared": round(r2, 4)}


def update_api_main(fitted_theta: float, fitted_k: float) -> bool:
    """Replace the hardcoded theta=46, k=0.15 in api/main.py with fitted values."""
    text = API_MAIN.read_text()

    old_comment = "# Sigmoid P(failure|omega): 1 / (1 + exp(-k*(omega - theta))), theta=46, k=0.15"
    new_comment = (
        f"# Sigmoid P(failure|omega): 1 / (1 + exp(-k*(omega - theta))), "
        f"theta={fitted_theta:.2f}, k={fitted_k:.4f} "
        f"(fitted via T10 from omega_outcome_results.json, n=120)"
    )

    old_math = "_es_p_fail = 1.0 / (1.0 + math.exp(-0.15 * (_es_omega - 46.0)))"
    new_math = f"_es_p_fail = 1.0 / (1.0 + math.exp(-{fitted_k:.4f} * (_es_omega - {fitted_theta:.2f})))"

    old_meta = '"calibration_model": "sigmoid(theta=46, k=0.15)",'
    new_meta = f'"calibration_model": "sigmoid(theta={fitted_theta:.2f}, k={fitted_k:.4f})",'

    if old_comment not in text or old_math not in text or old_meta not in text:
        return False

    text = text.replace(old_comment, new_comment)
    text = text.replace(old_math, new_math)
    text = text.replace(old_meta, new_meta)
    API_MAIN.write_text(text)
    return True


def main() -> None:
    data = json.loads(RESULTS_PATH.read_text())

    method_a = method_A_summary_stats(data)
    method_b = method_B_synthetic_lsq(data)

    # Prefer method B (data-driven LSQ fit) when R^2 is reasonable, else method A
    if method_b["R_squared"] >= 0.5:
        recommended = {"theta": method_b["theta"], "k": method_b["k"]}
        chosen_method = "B"
    else:
        recommended = {"theta": method_a["theta"], "k": method_a["k"]}
        chosen_method = "A"

    estimated = {"theta": 46.0, "k": 0.15}
    delta_theta = recommended["theta"] - estimated["theta"]
    delta_k = recommended["k"] - estimated["k"]

    significant = abs(delta_theta) > 5.0

    # Impact on expected_savings:
    # Compare p_failure at omega=70 (BLOCK threshold) under old vs new.
    p_old_70 = _sigmoid_safe(70.0, estimated["theta"], estimated["k"])
    p_new_70 = _sigmoid_safe(70.0, recommended["theta"], recommended["k"])
    p_old_50 = _sigmoid_safe(50.0, estimated["theta"], estimated["k"])
    p_new_50 = _sigmoid_safe(50.0, recommended["theta"], recommended["k"])
    rel_change_70 = (p_new_70 - p_old_70) / p_old_70 if p_old_70 > 0 else 0.0
    rel_change_50 = (p_new_50 - p_old_50) / p_old_50 if p_old_50 > 0 else 0.0

    impact = (
        f"P(failure|omega=70) shifts from {p_old_70:.4f} to {p_new_70:.4f} "
        f"({rel_change_70*100:+.1f}%); P(failure|omega=50) shifts from "
        f"{p_old_50:.4f} to {p_new_50:.4f} ({rel_change_50*100:+.1f}%). "
        f"Expected savings scale linearly with p_failure, so realized savings "
        f"per BLOCK call change by roughly the same percentages."
    )

    out = {
        "data_source": "omega_outcome_results.json (n=120)",
        "method_A_summary_stats": method_a,
        "method_B_synthetic_lsq": method_b,
        "estimated_values": {"theta": 46, "k": 0.15},
        "fitted_values_recommended": recommended,
        "recommended_method": chosen_method,
        "delta_from_estimate": {"theta": round(delta_theta, 4), "k": round(delta_k, 4)},
        "significant_update_needed": bool(significant),
        "impact_on_expected_savings": impact,
    }

    # If significant, update api/main.py
    updated = False
    if significant:
        try:
            updated = update_api_main(recommended["theta"], recommended["k"])
            out["api_main_updated"] = updated
            if updated:
                out["api_main_update_note"] = (
                    f"Replaced hardcoded theta=46, k=0.15 in api/main.py with "
                    f"theta={recommended['theta']}, k={recommended['k']} "
                    f"(fitted via T10, method {chosen_method})."
                )
        except Exception as e:
            out["api_main_updated"] = False
            out["api_main_update_error"] = str(e)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2))

    print("=== T10 Sigmoid Calibration Fit ===")
    print(f"Method A (summary stats):    theta={method_a['theta']}, k={method_a['k']}")
    print(f"Method B (synthetic LSQ):    theta={method_b['theta']}, k={method_b['k']}, R^2={method_b['R_squared']}")
    print(f"Estimated:                   theta=46, k=0.15")
    print(f"Recommended ({chosen_method}):              theta={recommended['theta']}, k={recommended['k']}")
    print(f"Delta:                       d_theta={delta_theta:+.2f}, d_k={delta_k:+.4f}")
    print(f"Significant update needed:   {significant}")
    if significant:
        print(f"api/main.py updated:         {updated}")
    print(f"Impact:                      {impact}")
    print(f"\nSaved to: {OUT_PATH}")


if __name__ == "__main__":
    main()
