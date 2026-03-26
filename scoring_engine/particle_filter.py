from __future__ import annotations
import math, hashlib
from dataclasses import dataclass
from typing import Optional

@dataclass
class ParticleFilterResult:
    state_estimate: float
    uncertainty: float
    effective_sample_size: float
    resampled: bool

def _hash_rand(seed: str, idx: int) -> float:
    h = int(hashlib.sha256(f"{seed}:{idx}".encode()).hexdigest()[:8], 16)
    return (h % 10000 - 5000) / 1000.0

def compute_particle_filter(omega: float, previous_particles: Optional[list[float]] = None, previous_weights: Optional[list[float]] = None, N: int = 50, seed: str = "pf") -> Optional[ParticleFilterResult]:
    try:
        if previous_particles and len(previous_particles) == N:
            particles = [p + _hash_rand(seed, i) * 5 for i, p in enumerate(previous_particles)]
            weights = previous_weights[:] if previous_weights and len(previous_weights) == N else [1.0/N]*N
        else:
            particles = [omega + _hash_rand(seed, i) * 5 for i in range(N)]
            weights = [1.0/N]*N
        # Update weights with likelihood
        for i in range(N):
            diff = omega - particles[i]
            weights[i] *= math.exp(-diff*diff / 200.0)
        w_sum = sum(weights) or 1.0
        weights = [w/w_sum for w in weights]
        ess = 1.0 / max(sum(w*w for w in weights), 1e-10)
        resampled = False
        if ess < N / 2:
            cum = []; s = 0
            for w in weights: s += w; cum.append(s)
            new_p = []
            for i in range(N):
                u = ((i + abs(_hash_rand(seed+"r", i)) % 1) / N) % 1.0
                for j in range(N):
                    if cum[j] >= u: new_p.append(particles[j]); break
                else: new_p.append(particles[-1])
            particles = new_p; weights = [1.0/N]*N
            ess = float(N); resampled = True
        est = sum(particles[i]*weights[i] for i in range(N))
        var = sum(weights[i]*(particles[i]-est)**2 for i in range(N))
        return ParticleFilterResult(state_estimate=round(est, 4), uncertainty=round(math.sqrt(max(var,0)), 4), effective_sample_size=round(ess, 2), resampled=resampled)
    except Exception: return None
