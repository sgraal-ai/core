# Omega as a Truncated Norm

## Definition

ω(**s**) = clamp(Σ wᵢsᵢ / S, 0, 100)

where S = Σ|wᵢ| and clamp(x, a, b) = max(a, min(b, x)).

## Properties

### P1: Non-negativity

ω(**s**) ≥ 0 for all **s** ∈ [0, 100]ⁿ — by construction (clamp lower bound = 0).

### P2: Definiteness

ω(**0**) = clamp(0 / S, 0, 100) = 0.

### P3: Subadditivity (pre-truncation)

For the un-clamped form ω̃(**s**) = Σwᵢsᵢ / S:

ω̃(**s** + **t**) = Σwᵢ(sᵢ + tᵢ) / S = ω̃(**s**) + ω̃(**t**)

This is strict equality (linearity), which implies subadditivity: ω̃(**s** + **t**) ≤ ω̃(**s**) + ω̃(**t**).

### Limitation: Not a true norm

1. **Bounded domain:** **s** ∈ [0, 100]ⁿ, not all of ℝⁿ
2. **Truncation breaks homogeneity:** ω(λ**s**) ≠ λω(**s**) when λ**s** exceeds [0, 100]ⁿ or ω > 100
3. **Negative weight:** s_recovery = -0.10 means the functional is not a seminorm on the positive orthant

## Conclusion

Omega is a **truncated weighted linear functional** on the bounded signal space [0, 100]ⁿ. It satisfies non-negativity (P1), definiteness (P2), and pre-truncation subadditivity (P3), making it norm-like but not a formal norm due to domain boundedness, truncation cap, and the negative recovery weight.
