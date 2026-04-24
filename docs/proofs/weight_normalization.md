# Weight Normalization Proof: ω ∈ [0, 100]

## Theorem

For any signal vector **s** = (s₁, ..., sₙ) where sᵢ ∈ [0, 100], the omega score ω(**s**) ∈ [0, 100].

## Definitions

- **W** = {w₁, ..., wₙ} — scoring weights (wᵢ ∈ ℝ, may be negative)
- **S** = Σ|wᵢ| — sum of absolute weights (currently S = 1.19)
- s_recovery weight = -0.10 (negative: recovery capability *reduces* risk)

## Proof

The raw weighted sum is:

ω_raw = Σ wᵢ × sᵢ

**Upper bound:** Maximum when all positive-weight components are at 100 and all negative-weight components are at 0:

ω_raw_max = Σ_{wᵢ>0} wᵢ × 100 = 100 × 1.09 = 109

**Lower bound:** Minimum when all positive-weight components are at 0 and all negative-weight components are at 100:

ω_raw_min = Σ_{wᵢ<0} wᵢ × 100 = -0.10 × 100 = -10

After normalization by S:

ω_norm = ω_raw / S ∈ [-10/1.19, 109/1.19] = [-8.4, 91.6]

After clamping:

**ω = max(0, min(100, ω_norm)) ∈ [0, 100]** □

## Implementation Reference

- `scoring_engine/omega_mem.py`, lines 287-291
- Weights: Σwᵢ = 0.99, Σ|wᵢ| = 1.19
- Negative weight: s_recovery = -0.10
- Clamping: `omega = max(0, min(100, omega))` — unconditional
