### 18.1 Ergodicity

Memory scoring is NOT ergodic across agent populations. In an ergodic system, the time average (one agent over many calls) equals the ensemble average (many agents at one moment). When this equality breaks, a single population-wide threshold is provably wrong for the agents whose personal distribution sits far from the crowd.

We simulated 50 agents with distinct risk personalities (15 low-risk, 20 medium-risk, 15 high-risk) and ran 30 preflight calls per agent (1500 observations total).

| Metric | Value |
| --- | --- |
| Ensemble mean Ω_MEM | 29.3508 |
| Ensemble std (across time steps) | 5.043 |
| Per-agent time-avg mean | 29.3508 |
| Per-agent time-avg std | 18.4002 |
| Per-agent time-avg range | [6.1933, 55.99] |
| KS statistic (time-avg vs ensemble) | 0.3 |
| Variance ratio (Var_time / Var_ensemble) | 13.3125 |
| Agents > ensemble + 10 | 15 |
| Agents < ensemble − 10 | 15 |
| Agents within ±10 of ensemble | 20 |
| Ergodic? | **False** |

**Implication:** population-level thresholds are miscalibrated for roughly 30 of 50 agents. Low-risk agents are under-served (BLOCK triggers earlier than their personal distribution warrants) and high-risk agents are over-trusted (their personal Ω_MEM baseline sits well above the population mean, so a global BLOCK=70 misses early-warning regimes). The `thresholds` field in `/v1/preflight` and per-agent calibration via the `/v1/calibration/*` endpoints exist precisely to address this — ergodicity violation is the formal justification.

