### 19.10 Koopman DMD with Delay Embedding

We ran Extended DMD with delay embedding (k=6) on the multivariate state [omega, s_freshness, s_drift, s_provenance, s_interference] across 50 agents over 56 days. A synthetic weekly degradation pattern was injected (Monday: age+=3, trust-=0.03; Tue-Thu mild; Fri-Sun recovery).

- Koopman modes extracted: **22**
- Self-correcting (|λ|<0.95): **21**
- Self-reinforcing (|λ|>1.05): **0**
- Marginal (|λ|≈1): **1**
- **Weekly structure recovered**: dominant period = **7.13 days** (target 7.00).

**Top 6 Koopman modes by magnitude:**

| # | λ_real | λ_imag | |λ| | Period (days) | Class |
|---|---:|---:|---:|---:|---|
| 1 | +1.0323 | +0.0000 | 1.0323 | — | marginal |
| 2 | +0.9338 | +0.0672 | 0.9362 | 87.48 | self-correcting |
| 3 | +0.9338 | -0.0672 | 0.9362 | 87.48 | self-correcting |
| 4 | +0.5831 | +0.7077 | 0.9170 | 7.13 | self-correcting |
| 5 | +0.5831 | -0.7077 | 0.9170 | 7.13 | self-correcting |
| 6 | +0.8594 | +0.0000 | 0.8594 | — | self-correcting |

**Interpretation.** Koopman DMD on 5-dim state × 50 agents × 56 days successfully recovered the injected weekly degradation cycle (dominant period = 7.13 days, target = 7.00). Of 22 Koopman modes, 21 are self-correcting (|λ|<0.95), 0 are self-reinforcing (|λ|>1.05), 1 are marginal.
