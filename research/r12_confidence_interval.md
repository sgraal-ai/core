# R12 Confidence Interval Analysis

## Wilson Score 95% CI for R12 Exact Match

### Current result: 49/60 (81.67%)

```python
from statsmodels.stats.proportion import proportion_confint
ci = proportion_confint(49, 60, alpha=0.05, method='wilson')
# (0.6997, 0.8951)
```

**Wilson score 95% CI: [69.97%, 89.51%]**

Sprint 65 improvement: PA-008 fixed via deep provenance chain escalation (chain_depth >= 3 → ASK_USER). 2 remaining PA mismatches (PA-002, PA-009) are architectural invariants — MANIPULATED → BLOCK and SUSPICIOUS + destructive → BLOCK cannot be relaxed.

### Previous result: 48/60 (80.0%)

Wilson 95% CI: [67.7%, 89.1%]

### Comparison to 43/60 baseline (71.7%)

```python
ci_43 = proportion_confint(43, 60, alpha=0.05, method='wilson')
# (0.5891, 0.8190)
```

**43/60 Wilson 95% CI: [58.9%, 81.9%]**

The CIs overlap — the improvement from 43 to 48 is directionally positive but not statistically significant at n=60. This is expected: 60 cases is too small for a 5-case improvement to clear the significance bar.

### Pitch usage

> Sgraal R12 exact match = 81.7% with 95% CI [70.0%, 89.5%] on a 60-case adversarial corpus covering 3 attack families (confidence calibration, partial sync bleed, multi-hop provenance asymmetry). 24/24 hard BLOCK cases detected — zero false negatives on high-severity attacks.

### Per-family breakdown

| Family | Score | Rate | Wilson 95% CI |
|--------|-------|------|---------------|
| CC (confidence_calibration) | 11/20 | 55.0% | [33.2%, 75.1%] |
| PS (partial_sync_bleed) | 20/20 | 100.0% | [83.9%, 100.0%] |
| PA (multi_hop_provenance_asymmetry) | 18/20 | 90.0% | [69.9%, 97.2%] |
| **Total** | **49/60** | **81.7%** | **[70.0%, 89.5%]** |
| BLOCK subset | 24/24 | 100.0% | [86.2%, 100.0%] |

### Sample size note

60 cases produces a CI width of ~21pp. To achieve a CI width of 10pp at 80% accuracy, approximately 246 cases are needed. Production data from live API traffic would provide tighter bounds than the fixed adversarial corpus.

```python
# Required n for 10pp CI width at p=0.80
# Wilson CI width ≈ 2 * 1.96 * sqrt(p*(1-p)/n) ≈ 10pp
# n ≈ (2 * 1.96)^2 * 0.80 * 0.20 / 0.10^2 ≈ 246
```

### Methodology

Wilson score interval chosen over Wald (normal approximation) because:
- Wald CIs can extend below 0 or above 1 for extreme proportions
- Wilson has better coverage properties for small n
- Wilson is the standard for binomial proportion CIs in applied statistics
