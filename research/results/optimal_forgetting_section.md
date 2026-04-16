### 19.7 Optimal Forgetting Rate per Domain

Each domain × forgetting-rate λ combination is simulated with 25 agents making 20 preflight calls each (500 calls / config). Memory ages progress by U[1,3] days per call, and each entry has per-call probability λ of being 'forgotten' and reset to age 0. Outcomes are synthetic (success P=0.9 if ω<40 else P=0.3); decision accuracy measures alignment between the recommended action and the outcome.

**Optimal λ per domain (argmax accuracy):**

| Domain | λ* (accuracy) | Accuracy | λ (min ω) | λ (max savings) |
|--------|---------------|----------|-----------|-----------------|
| general | 0.005 | 0.120 | 0.5 | 0.001 |
| fintech | 0.001 | 0.278 | 0.5 | 0.001 |
| medical | 0.001 | 0.338 | 0.5 | 0.001 |
| legal | 0.001 | 0.174 | 0.5 | 0.001 |
| coding | 0.1 | 0.112 | 0.5 | 0.001 |
| customer_support | 0.2 | 0.126 | 0.5 | 0.001 |

High-criticality domains (fintech/medical/legal) prefer *lower* forgetting rates than lower-criticality domains (coding/customer_support/general). Under irreversible actions, retaining older evidence is worth the risk of some staleness; under reversible actions, faster turnover pays off.

Suggested defaults (per domain, argmax accuracy): general→λ=0.005, fintech→λ=0.001, medical→λ=0.001, legal→λ=0.001, coding→λ=0.1, customer_support→λ=0.2

_Synthetic: the outcome model is a threshold sigmoid at ω=40, not a real-world label set. The optimal λ values here should be validated on production outcomes before being used as scheduling defaults._
