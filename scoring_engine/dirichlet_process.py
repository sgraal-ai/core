from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional

@dataclass
class DirichletProcessResult:
    n_clusters: int
    cluster_assignments: list[int]
    new_cluster_detected: bool
    concentration: float

def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(x*x for x in b))
    return dot/(na*nb) if na>0 and nb>0 else 0.0

def _entry_vec(e: dict) -> list[float]:
    return [e.get("source_trust",0.5)*100, max(0,100-e.get("timestamp_age_days",0)),
            (1-(e.get("source_conflict",0.1) or 0.1))*100, max(0,100-e.get("downstream_count",0)*10)]

def compute_dirichlet_process(entries: list[dict], alpha: float = 1.0, sim_threshold: float = 0.7) -> Optional[DirichletProcessResult]:
    if not entries: return None
    try:
        vecs = [_entry_vec(e) for e in entries]
        clusters, centroids = [], []
        new_detected = False
        cluster_counts = [1] * len(centroids)
        for i,v in enumerate(vecs):
            assigned = False
            for ci,cent in enumerate(centroids):
                if _cosine(v, cent) > sim_threshold:
                    clusters.append(ci)
                    n = cluster_counts[ci]
                    centroids[ci] = [(cent[d]*n+v[d])/(n+1) for d in range(len(v))]
                    cluster_counts[ci] += 1
                    assigned = True; break
            if not assigned:
                p_new = alpha / (i + alpha)
                clusters.append(len(centroids))
                centroids.append(v[:])
                cluster_counts.append(1)
                if i > 0: new_detected = True
        return DirichletProcessResult(n_clusters=len(centroids), cluster_assignments=clusters, new_cluster_detected=new_detected, concentration=alpha)
    except Exception: return None
