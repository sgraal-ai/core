### 19.9 Optimal Transport Between BLOCK and USE_MEMORY

We treat the `/v1/preflight` output space as a measure space and ask: how far apart are the BLOCK and USE_MEMORY conditional distributions, and what is the minimum-effort trajectory from a BLOCKed state toward safety?

**Setup.**

- 175 BLOCK samples vs 124 USE_MEMORY samples
- 77-dimensional standardized feature space (zero-variance columns and `omega_mem_final` excluded)
- Entropic OT: Sinkhorn with epsilon=0.1, cost = euclidean distance

**Wasserstein distance:**

| Quantity | Value |
|---|---|
| W_epsilon (standardized) | **13.479** |
| W_epsilon (raw units) | 211580.717 |
| Sinkhorn iterations | 6 |
| Converged | True |

A non-trivial Wasserstein distance between BLOCK and USE_MEMORY confirms the two decision classes occupy distinct regions of feature space — the preflight engine does not merely threshold one or two features but induces a geometric separation.

**Barycenter (safe-recovery center).** We define the safe-recovery center as

```
barycenter = 0.3 * mean(BLOCK) + 0.7 * mean(USE_MEMORY)
```

biased toward the safe cluster. Each BLOCK point is then at an average euclidean distance of **10.57 sigmas** (median 9.85, p95 17.82) from this center — the mean L2 'healing effort' required.

**Top healing-direction features.** Features whose BLOCK cluster mean is furthest from the barycenter, in sigma-units — these are the components the repair plan must preferentially move.

| Feature | block_mean | use_memory_mean | delta (sigmas) |
|---|---|---|---|
| `koopman.prediction_5` | 91.811 | 5.370 | -1.61 |
| `lqr_control.optimal_control` | -33.025 | 38.166 | +1.61 |
| `banach_contraction.fixed_point_estimate` | 86.327 | 8.018 | -1.61 |
| `lqr_control.state_deviation` | 36.327 | -41.982 | -1.61 |
| `particle_filter.state_estimate` | 86.253 | 8.009 | -1.61 |
| `mdp_recommendation.expected_value` | 9.114 | 9.461 | +1.57 |
| `shapley_values.mean` | 7.548 | 1.399 | -1.56 |
| `drift_details.kl_divergence` | 21.990 | 65.903 | +1.47 |
| `info_thermodynamics.information_temperature` | 17.796 | 43.122 | +1.45 |
| `drift_details.jsd` | 8.773 | 24.458 | +1.42 |

**Implication.** A repair plan can be interpreted as an approximate OT transport map: each BLOCK point is pushed along the direction of largest sigma-change toward the barycenter. The top-ranked features above indicate which components carry the most transport mass, and therefore which heal actions (REFETCH, VERIFY_WITH_SOURCE, etc.) yield the greatest reduction in Wasserstein distance per unit of effort.

**Caveat.** The barycenter used here is the weighted mean specified in the task (fast, interpretable) rather than the true Wasserstein-barycenter fixed point. For production repair plan prioritization, a full iterative barycenter solver would give a more geometrically accurate target, at ~10x compute cost.
