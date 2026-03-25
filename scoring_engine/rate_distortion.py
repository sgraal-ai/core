from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class EntryRetention:
    entry_id: str
    information_value: float
    distortion_cost: float
    keep_score: float
    recommend_delete: bool


@dataclass
class RateDistortionResult:
    entries: list[EntryRetention]
    total_rate: float
    total_distortion: float
    compression_ratio: float
    deletable_count: int
    lambda_used: float


def _entry_entropy(scores: list[float]) -> float:
    """Shannon entropy H(X) = -Σ p·log(p) over component scores."""
    total = sum(scores) or 1.0
    probs = [s / total for s in scores if s > 0]
    if not probs:
        return 0.0
    return -sum(p * math.log(p + 1e-10) for p in probs)


def _entry_distortion(scores: list[float], global_mean: list[float]) -> float:
    """MSE distortion between entry scores and global mean."""
    n = min(len(scores), len(global_mean))
    if n == 0:
        return 0.0
    return sum((scores[i] - global_mean[i]) ** 2 for i in range(n)) / n


def compute_rate_distortion(
    entries: list[dict],
    omega_mem_final: float,
    component_breakdown: dict,
    system_health: Optional[float] = None,
    keep_threshold: float = 0.3,
    omega_threshold: float = 40.0,
) -> Optional[RateDistortionResult]:
    """Rate-Distortion optimum for memory retention decisions.

    γ(t) = argmin[I(X;X̂) + λ·E[d(X,X̂)]]

    Per-entry:
        information_value = H(entry) = -Σ p·log(p) over component scores
        distortion_cost = MSE from global mean
        keep_score = information_value / (distortion_cost + ε)
        recommend_delete when keep_score < threshold AND omega < omega_threshold

    λ = 0.5 * (1 - system_health/100), dynamically scaled.

    Args:
        entries: list of dicts with id, source_trust, timestamp_age_days, etc.
        omega_mem_final: current omega score
        component_breakdown: dict of component scores from scoring
        system_health: average omega across entries (0-100), None for default λ=0.5
        keep_threshold: keep_score below this → recommend_delete (default 0.3)
        omega_threshold: omega below this enables deletion (default 40.0)

    Returns:
        RateDistortionResult or None on error
    """
    if not entries:
        return None

    try:
        n = len(entries)

        # Dynamic λ: compression-distortion tradeoff
        if system_health is not None:
            lambda_used = 0.5 * (1.0 - system_health / 100.0)
            lambda_used = max(0.0, min(1.0, lambda_used))
        else:
            lambda_used = 0.5

        # Build per-entry score vectors from available metadata
        entry_scores = []
        for e in entries:
            scores = [
                e.get("source_trust", 0.5) * 100,
                max(0, 100 - e.get("timestamp_age_days", 0)),
                (1.0 - e.get("source_conflict", 0.1)) * 100 if e.get("source_conflict") is not None else 90,
                max(0, 100 - e.get("downstream_count", 0) * 10),
            ]
            entry_scores.append(scores)

        # Global mean for distortion reference
        dim = len(entry_scores[0]) if entry_scores else 0
        if n >= 2 and dim > 0:
            global_mean = [sum(entry_scores[i][d] for i in range(n)) / n for d in range(dim)]
        else:
            global_mean = entry_scores[0] if entry_scores else [50.0] * dim

        # Per-entry retention analysis
        results = []
        total_rate = 0.0
        total_distortion = 0.0
        deletable = 0

        for idx, e in enumerate(entries):
            scores = entry_scores[idx]

            # Information value: Shannon entropy
            info_val = round(_entry_entropy(scores), 4)
            total_rate += info_val

            # Distortion cost: MSE from global mean
            dist_cost = round(_entry_distortion(scores, global_mean), 4)
            total_distortion += dist_cost

            # Keep score: information / (distortion + ε)
            eps = 0.01
            keep = round(info_val / (dist_cost + eps), 4)

            # Recommend delete: low keep_score AND low omega
            rec_delete = keep < keep_threshold and omega_mem_final < omega_threshold

            if rec_delete:
                deletable += 1

            results.append(EntryRetention(
                entry_id=e.get("id", f"entry_{idx}"),
                information_value=info_val,
                distortion_cost=dist_cost,
                keep_score=keep,
                recommend_delete=rec_delete,
            ))

        compression_ratio = round(deletable / max(n, 1), 4)

        return RateDistortionResult(
            entries=results,
            total_rate=round(total_rate, 4),
            total_distortion=round(total_distortion, 4),
            compression_ratio=compression_ratio,
            deletable_count=deletable,
            lambda_used=round(lambda_used, 4),
        )
    except Exception:
        return None
