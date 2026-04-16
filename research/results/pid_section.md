### 19.8 Partial Information Decomposition (Simplified Proxy)

Full Williams-Beer PID over 132 features is combinatorially prohibitive, so we compute a pairwise proxy based on interaction information:

```
II(X_i ; X_j ; omega) = MI(X_i ; omega) + MI(X_j ; omega) - MI((X_i,X_j) ; omega)
redundancy(i,j)  = min(MI_i, MI_j) * |cos(X_i, X_j)|
synergy(i,j)     = | MI_joint - MI_i - MI_j + redundancy |
unique_info(i)   = MI_i - E_j [ MI(X_j ; omega | X_i) ]
```

All 449 benchmark cases were run through `/v1/preflight`; we standardized 77 active numeric features (dropping 54 zero-variance columns and the target `omega_mem_final` itself), discretized each to 10 bins, and estimated MI in nats via 2D histograms.

**Module classification:**

| Class | Rule | Count |
|---|---|---|
| ESSENTIAL | unique MI > 0.1 nats AND ≤ 3 high-red partners | **1** |
| DUPLICATE | > 3 high-red partners (above pair-redundancy q75 = 0.351) | **28** |
| SYNERGISTIC | best pair synergy > 0.05 nats | **11** |

**Essential modules (top 10 by MI with omega):**

- `copula_analysis.joint_risk` — MI=0.477, unique=0.115, red_partners=2

**Top 5 redundant pairs (near-duplicate information):**

| A | B | redundancy | cos |
|---|---|---|---|
| `lqr_control.state_deviation` | `banach_contraction.fixed_point_estimate` | 2.200 | 1.000 |
| `lqr_control.state_deviation` | `lqr_control.optimal_control` | 2.200 | -1.000 |
| `banach_contraction.fixed_point_estimate` | `lqr_control.optimal_control` | 2.200 | -1.000 |
| `lqr_control.state_deviation` | `particle_filter.state_estimate` | 1.841 | 0.999 |
| `banach_contraction.fixed_point_estimate` | `particle_filter.state_estimate` | 1.841 | 0.999 |

**Top 5 synergistic pairs (information together > information apart):**

| A | B | synergy | MI_joint |
|---|---|---|---|
| `lqr_control.state_deviation` | `calibration.brier_score` | 1.872 | 1.755 |
| `banach_contraction.fixed_point_estimate` | `calibration.brier_score` | 1.872 | 1.755 |
| `lqr_control.optimal_control` | `calibration.brier_score` | 1.872 | 1.755 |
| `lqr_control.optimal_control` | `lqr_control.control_effort` | 1.803 | 1.832 |
| `lqr_control.state_deviation` | `lqr_control.control_effort` | 1.792 | 1.843 |

**Interpretation.** The scoring stack is dominated by DUPLICATE modules — a direct empirical confirmation of the Risk Polytope compression finding: 132 features collapse onto a low-dimensional manifold, so most pairs carry overlapping information about `omega_mem_final`. Under our strict definition (unique MI > 0.1 nats AND ≤ 3 high-redundancy partners) only a single module qualifies as ESSENTIAL: `copula_analysis.joint_risk`. A larger set of modules passes the unique-MI bar but has too many redundant partners to be irreducible. Synergistic pairs reveal where ensemble gains are real — typically cross-family combinations (a geometric/control signal paired with a calibration or probabilistic signal).

**Caveat.** This is a simplified proxy — not the true Williams-Beer PID lattice. The `unique_info` estimator uses an aggregated reference Y (mean of sampled other features) rather than a redundancy lattice, and the synergy estimator relies on 4×4 equal-frequency binning of `(X_i, X_j)`. Results should be treated as rankings, not calibrated information measures.
