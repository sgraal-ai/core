### 18.3 Granger Causality and Early Warning

We simulated 20 agents over 50 calls each (1000 observations, 345 BLOCK events) with monotonically degrading memory (age rising, trust eroding, conflict growing). For each candidate module X, we computed lagged correlation corr(X_{t-k}, 1[action_t = BLOCK]) for k ∈ {1,2,3,5,7,10} and selected the lag that maximised |r|, pooling across agents with weighted means.

**Leading indicators** (peak |r|, Granger-style lag):

| Module | r | Lag (calls) | p |
|---|---:|---:|---:|
| `mewma_t2` | +0.906 | 3 | 0.0000 |
| `s_interference` | +0.837 | 10 | 0.0000 |
| `s_provenance` | +0.836 | 10 | 0.0000 |
| `copula_joint_risk` | +0.828 | 10 | 0.0000 |
| `s_freshness` | +0.809 | 10 | 0.0000 |
| `s_drift` | +0.788 | 10 | 0.0000 |
| `r_recall` | +0.775 | 10 | 0.0000 |
| `free_energy_surprise` | +0.397 | 10 | 0.0000 |

**Predictive accuracy** — threshold predictor over the top-3 leaders:

| Horizon | Accuracy | Precision | Recall |
|---|---:|---:|---:|
| 5 calls ahead | 97.45% | 99.51% | 94.63% |
| 10 calls ahead | 96.53% | 97.50% | 96.02% |
| 20 calls ahead | 95.41% | 98.58% | 95.19% |

**Operational implication.** Preflight now exposes an `early_warning_signals` array that fires when a leading indicator crosses its empirical threshold while the current decision is still USE_MEMORY/WARN/ASK_USER. This converts the scoring engine from a reactive gate into a predictive one: callers can heal, refetch, or escalate before the BLOCK lands.
