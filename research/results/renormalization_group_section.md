### 19.12 Renormalization Group Flow

We simulated 5000 preflight calls per domain across all 6 domains (30,000 total) with randomised memory states, then applied block-spin coarse-graining at three scales (N=1 per-call, N=60 per-hour, N=100 per-day).

**Moments per domain at finest (N=1) scale:**

| Domain | mean | std | skew | kurt | tail α | class |
|---|---:|---:|---:|---:|---:|---|
| general | 46.66 | 21.91 | +0.66 | 2.76 | 7.65 | mean_field_like |
| customer_support | 55.01 | 24.25 | +0.41 | 2.17 | 24.43 | trivial |
| coding | 59.47 | 25.04 | +0.22 | 1.95 | ∞ | trivial |
| legal | 69.31 | 24.86 | -0.19 | 1.84 | ∞ | trivial |
| fintech | 74.72 | 23.90 | -0.48 | 2.07 | ∞ | trivial |
| medical | 78.83 | 23.00 | -0.75 | 2.44 | ∞ | trivial |

**Moments per domain at coarsest (N=100) scale:**

| Domain | mean | std | skew | kurt |
|---|---:|---:|---:|---:|
| general | 46.66 | 2.36 | +0.26 | 2.55 |
| customer_support | 55.01 | 1.89 | -0.20 | 2.40 |
| coding | 59.47 | 2.28 | -0.24 | 3.15 |
| legal | 69.31 | 2.65 | +0.02 | 2.07 |
| fintech | 74.72 | 2.05 | +0.14 | 2.50 |
| medical | 78.83 | 2.05 | +0.11 | 2.18 |

**Pairwise KS distance at coarsest scale** (mean = 0.941, max = 1.000):

| A | B | KS |
|---|---|---:|
| general | customer_support | 0.960 |
| general | coding | 1.000 |
| general | legal | 1.000 |
| general | fintech | 1.000 |
| general | medical | 1.000 |
| customer_support | coding | 0.720 |
| customer_support | legal | 1.000 |
| customer_support | fintech | 1.000 |
| customer_support | medical | 1.000 |
| coding | legal | 0.980 |

**Interpretation.** Domains do NOT converge to a shared fixed point: max pairwise KS at coarsest scale = 1.000 (>0.2). Each domain has a distinct macroscopic distribution. Universality classes: 1 mean-field-like, 0 critical, 5 trivial. Mean pairwise KS at coarsest scale: 0.941.
