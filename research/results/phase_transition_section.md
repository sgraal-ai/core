### 19.5 Phase Transition Conjecture

We scored 449 benchmark corpus cases through `/v1/preflight` (dry-run, `score_history=[50]*10` to activate temporal modules) and tracked three collapse signals versus `omega_mem_final`: spectral Fiedler value λ₂, HMM critical-state probability, and Hawkes intensity λ.

| ω band | n | mean λ₂ | mean HMM-crit | mean Hawkes |
|--------|---|---------|---------------|-------------|
| 0-10 | 72 | 0.8279 | 0.0000 | 0.1644 |
| 10-20 | 50 | 0.1581 | 0.0000 | 0.2569 |
| 20-30 | 30 | 0.2147 | 0.0000 | 0.1768 |
| 30-40 | 28 | 0.4954 | 0.0000 | 0.1635 |
| 40-50 | 41 | 0.1940 | 0.0000 | 0.2806 |
| 50-60 | 47 | 0.0559 | 0.0000 | 0.2783 |
| 60-70 | 38 | 0.0320 | 0.0000 | 0.2536 |
| 70-80 | 34 | 0.0000 | 0.0000 | 0.2004 |
| 80-90 | 17 | 0.1711 | 0.0000 | 0.1241 |
| 90-100 | 92 | 0.0418 | 0.0000 | 0.2251 |

**Empirical critical ω (max |Δsignal/Δω|):** 10  
**Peak-to-mean derivative ratio:** 2.90  
**Transition classification:** `first_order`  
**Power-law exponent (|ω − ω_c| fit):** -0.141

A first-order-like discontinuity is observed near omega ~ 10. The combined (λ₂, HMM-critical, Hawkes) signal derivative spikes sharply at this boundary, indicating that memory system behaviour flips rather than drifts as omega crosses this point.

_Synthetic: results are derived from dry-run scoring on the packaged benchmark corpus and should be corroborated on production decision data before being used to move action thresholds._
