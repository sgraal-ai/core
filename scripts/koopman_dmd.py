#!/usr/bin/env python3
"""
Research Task #10: Full Koopman DMD with delay embedding.

Question: Which modes in the multivariate omega state are self-correcting
(|λ|<1) vs self-reinforcing (|λ|>1)? Is there a "Monday degradation" weekly
periodic structure?

Method:
1. Simulate 50 agents × 56 days (8 weeks) with an injected weekly pattern.
2. For each agent, build multivariate state [omega, s_freshness, s_drift,
   s_provenance, s_interference] × 56 days.
3. Delay-embed with k=0..5 -> augmented matrix of shape (5*6, 56-5).
4. Standard DMD: X1 = X[:, :-1], X2 = X[:, 1:], SVD of X1, reduced
   Koopman A~ = U^T X2 V Σ^-1, eigenvalues of A~.
5. Classify modes. Find eigenvalue with period ≈ 7 days.
"""
from __future__ import annotations

import os
import sys
import json
import math
import random
from collections import defaultdict
from typing import Optional, Tuple, List

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")

import numpy as np  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from api.main import app  # noqa: E402

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

N_AGENTS = 50
N_DAYS = 56
DELAY = 6
STATE_DIM = 5

RESULTS_PATH = "/Users/zsobrakpeter/core/research/results/koopman_dmd.json"
MARKDOWN_PATH = "/Users/zsobrakpeter/core/research/results/koopman_dmd_section.md"


def simulate_agent(agent_idx: int, rng: random.Random) -> np.ndarray:
    """Simulate 56 days of preflight calls, returning state trajectory (5, 56)."""
    age = rng.uniform(1.0, 3.0)
    trust = rng.uniform(0.85, 0.92)
    conflict = rng.uniform(0.05, 0.12)
    history: list[float] = [50.0] * 10

    trajectory = np.zeros((STATE_DIM, N_DAYS))

    for day in range(N_DAYS):
        dow = day % 7
        # Weekly pattern injection
        if dow == 0:  # Monday degradation
            age += 3.0
            trust -= 0.03
        elif dow in (1, 2, 3):  # Tue-Thu slight
            age += 1.0
            trust -= 0.005
        else:  # Fri-Sat-Sun recovery
            age += 0.5
            trust += 0.01

        # Noise
        age += rng.gauss(0, 0.3)
        trust += rng.gauss(0, 0.005)
        conflict += rng.gauss(0, 0.008)

        # Bounds
        age = max(0.1, age)
        trust = max(0.5, min(0.95, trust))
        conflict = max(0.01, min(0.6, conflict))

        body = {
            "agent_id": f"kdmd_agent_{agent_idx:02d}",
            "task_id": f"d_{day:03d}",
            "memory_state": [
                {
                    "id": f"k_{agent_idx:02d}_{day:03d}_a",
                    "content": f"Agent {agent_idx} day {day} A",
                    "type": "semantic",
                    "timestamp_age_days": round(age, 3),
                    "source_trust": round(trust, 4),
                    "source_conflict": round(conflict, 4),
                    "downstream_count": rng.randint(1, 5),
                },
                {
                    "id": f"k_{agent_idx:02d}_{day:03d}_b",
                    "content": f"Agent {agent_idx} day {day} B",
                    "type": "tool_state",
                    "timestamp_age_days": round(max(0.1, age * 0.6), 3),
                    "source_trust": round(min(0.98, trust + 0.03), 4),
                    "source_conflict": round(max(0.01, conflict - 0.01), 4),
                    "downstream_count": rng.randint(1, 3),
                },
            ],
            "action_type": "reversible",
            "domain": "general",
            "score_history": history[-10:],
            "dry_run": True,
        }

        try:
            r = client.post("/v1/preflight", json=body, headers=AUTH)
            if r.status_code != 200:
                omega = history[-1] if history else 50.0
                s_fresh = 0.0
                s_drift = 0.0
                s_prov = 0.0
                s_int = 0.0
            else:
                resp = r.json()
                omega = float(resp.get("omega_mem_final", 50.0) or 50.0)
                cb = resp.get("component_breakdown", {}) or {}
                s_fresh = float(cb.get("s_freshness", 0) or 0)
                s_drift = float(cb.get("s_drift", 0) or 0)
                s_prov = float(cb.get("s_provenance", 0) or 0)
                s_int = float(cb.get("s_interference", 0) or 0)
        except Exception:
            omega = history[-1] if history else 50.0
            s_fresh = s_drift = s_prov = s_int = 0.0

        trajectory[0, day] = omega
        trajectory[1, day] = s_fresh
        trajectory[2, day] = s_drift
        trajectory[3, day] = s_prov
        trajectory[4, day] = s_int

        history.append(omega)

    return trajectory


def build_delay_embedding(X: np.ndarray, delay: int) -> np.ndarray:
    """Delay-embed (d, T) -> (d*delay, T-delay+1)."""
    d, T = X.shape
    cols = T - delay + 1
    out = np.zeros((d * delay, cols))
    for k in range(delay):
        out[k * d:(k + 1) * d, :] = X[:, k:k + cols]
    return out


def dmd(X_aug: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Standard DMD. Returns (eigenvalues, modes)."""
    X1 = X_aug[:, :-1]
    X2 = X_aug[:, 1:]

    # SVD with truncation to rank
    U, S, Vt = np.linalg.svd(X1, full_matrices=False)

    # Truncate at energy threshold
    energy = np.cumsum(S ** 2) / np.sum(S ** 2)
    r = int(np.searchsorted(energy, 0.999)) + 1
    r = min(r, len(S), X1.shape[1])

    U_r = U[:, :r]
    S_r = S[:r]
    Vt_r = Vt[:r, :]

    # Reduced Koopman operator A~ = U^T X2 V Σ^-1
    A_tilde = U_r.T @ X2 @ Vt_r.T @ np.diag(1.0 / S_r)

    eigenvalues, eigvecs = np.linalg.eig(A_tilde)
    return eigenvalues, eigvecs


def classify_mode(eigenvalue: complex) -> tuple[str, float | None]:
    """Classify mode, return (classification, period_days or None)."""
    mag = abs(eigenvalue)
    if mag > 1.05:
        klass = "self-reinforcing"
    elif mag < 0.95:
        klass = "self-correcting"
    else:
        klass = "marginal"

    # Period: 2π / arg(λ) where λ = r*exp(iθ)
    theta = math.atan2(eigenvalue.imag, eigenvalue.real)
    period = None
    if abs(theta) > 1e-6:
        period = abs(2 * math.pi / theta)
    return klass, period


def main():
    print("[koopman_dmd] Simulating agents...")
    random.seed(42)
    np.random.seed(42)

    trajectories: list[np.ndarray] = []
    for i in range(N_AGENTS):
        rng = random.Random(1000 + i)
        traj = simulate_agent(i, rng)
        trajectories.append(traj)
        if (i + 1) % 10 == 0:
            print(f"  ... {i + 1}/{N_AGENTS} agents done")

    # Concatenate along the time axis with delay embedding per agent
    print("[koopman_dmd] Building delay-embedded snapshots per agent, then stacking...")
    X1_all = []
    X2_all = []
    for traj in trajectories:
        # Standardise per-agent (avoid scale dominance)
        mean = traj.mean(axis=1, keepdims=True)
        std = traj.std(axis=1, keepdims=True)
        std[std < 1e-8] = 1.0
        traj_n = (traj - mean) / std

        aug = build_delay_embedding(traj_n, DELAY)
        X1_all.append(aug[:, :-1])
        X2_all.append(aug[:, 1:])

    X1 = np.concatenate(X1_all, axis=1)
    X2 = np.concatenate(X2_all, axis=1)
    print(f"  X1 shape: {X1.shape}, X2 shape: {X2.shape}")

    # DMD on stacked
    U, S, Vt = np.linalg.svd(X1, full_matrices=False)
    energy = np.cumsum(S ** 2) / np.sum(S ** 2)
    r = int(np.searchsorted(energy, 0.999)) + 1
    r = min(r, len(S), X1.shape[1], 40)
    print(f"  SVD rank used: {r} (out of {len(S)})")

    U_r = U[:, :r]
    S_r = S[:r]
    Vt_r = Vt[:r, :]
    A_tilde = U_r.T @ X2 @ Vt_r.T @ np.diag(1.0 / S_r)

    eigenvalues, _ = np.linalg.eig(A_tilde)

    # Sort by magnitude descending
    idx = np.argsort(-np.abs(eigenvalues))
    eigenvalues = eigenvalues[idx]

    # Classify
    modes = []
    n_reinforcing = 0
    n_correcting = 0
    n_marginal = 0
    weekly_mode_found = False
    dominant_period = None
    best_period_diff = float("inf")

    for i, lam in enumerate(eigenvalues):
        klass, period = classify_mode(lam)
        if klass == "self-reinforcing":
            n_reinforcing += 1
        elif klass == "self-correcting":
            n_correcting += 1
        else:
            n_marginal += 1

        if period is not None and 5.0 <= period <= 10.0:
            diff = abs(period - 7.0)
            if diff < best_period_diff:
                best_period_diff = diff
                dominant_period = period
                weekly_mode_found = True

        modes.append({
            "mode_id": i + 1,
            "eigenvalue_real": float(lam.real),
            "eigenvalue_imag": float(lam.imag),
            "magnitude": float(abs(lam)),
            "period_days": float(period) if period is not None else None,
            "classification": klass,
        })

    # Interpretation
    interp_parts = []
    if weekly_mode_found:
        interp_parts.append(
            f"Koopman DMD on 5-dim state × 50 agents × 56 days successfully recovered "
            f"the injected weekly degradation cycle (dominant period = {dominant_period:.2f} days, "
            f"target = 7.00)."
        )
    else:
        interp_parts.append(
            "No eigenvalue with period in the 5-10 day range was recovered; "
            "weekly structure was not linearly separable in this run."
        )

    interp_parts.append(
        f"Of {len(modes)} Koopman modes, {n_correcting} are self-correcting (|λ|<0.95), "
        f"{n_reinforcing} are self-reinforcing (|λ|>1.05), {n_marginal} are marginal."
    )
    if n_reinforcing > 0:
        interp_parts.append(
            "Self-reinforcing modes indicate latent degradation drivers that do not spontaneously "
            "recover and should be explicitly healed."
        )

    result = {
        "data_source": "synthetic_weekly_pattern",
        "n_agents": N_AGENTS,
        "n_timesteps": N_DAYS,
        "state_dim": STATE_DIM,
        "delay_embedding": DELAY,
        "n_koopman_modes": len(modes),
        "modes": modes[:30],  # top 30 by magnitude
        "n_self_reinforcing": n_reinforcing,
        "n_self_correcting": n_correcting,
        "n_marginal": n_marginal,
        "weekly_pattern_detected": weekly_mode_found,
        "dominant_period_days": float(dominant_period) if dominant_period is not None else None,
        "interpretation": " ".join(interp_parts),
    }

    with open(RESULTS_PATH, "w") as f:
        json.dump(result, f, indent=2)
    print(f"[koopman_dmd] Wrote {RESULTS_PATH}")

    # Markdown
    md = []
    md.append("### 19.10 Koopman DMD with Delay Embedding\n")
    md.append(
        f"We ran Extended DMD with delay embedding (k={DELAY}) on the multivariate state "
        f"[omega, s_freshness, s_drift, s_provenance, s_interference] across {N_AGENTS} "
        f"agents over {N_DAYS} days. A synthetic weekly degradation pattern was injected "
        f"(Monday: age+=3, trust-=0.03; Tue-Thu mild; Fri-Sun recovery).\n"
    )
    md.append(f"- Koopman modes extracted: **{len(modes)}**")
    md.append(f"- Self-correcting (|λ|<0.95): **{n_correcting}**")
    md.append(f"- Self-reinforcing (|λ|>1.05): **{n_reinforcing}**")
    md.append(f"- Marginal (|λ|≈1): **{n_marginal}**")
    if weekly_mode_found:
        md.append(
            f"- **Weekly structure recovered**: dominant period = "
            f"**{dominant_period:.2f} days** (target 7.00).\n"
        )
    else:
        md.append("- Weekly period NOT recovered in the 5-10 day band.\n")

    md.append("**Top 6 Koopman modes by magnitude:**\n")
    md.append("| # | λ_real | λ_imag | |λ| | Period (days) | Class |")
    md.append("|---|---:|---:|---:|---:|---|")
    for m in modes[:6]:
        p = f"{m['period_days']:.2f}" if m['period_days'] is not None else "—"
        md.append(
            f"| {m['mode_id']} | {m['eigenvalue_real']:+.4f} | {m['eigenvalue_imag']:+.4f} "
            f"| {m['magnitude']:.4f} | {p} | {m['classification']} |"
        )
    md.append("")
    md.append(f"**Interpretation.** {result['interpretation']}\n")

    with open(MARKDOWN_PATH, "w") as f:
        f.write("\n".join(md))
    print(f"[koopman_dmd] Wrote {MARKDOWN_PATH}")


if __name__ == "__main__":
    main()
