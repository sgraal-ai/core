# Weight Normalization Theorem

## Statement

For any component vector **c** ∈ [0, 100]ⁿ and weight vector **w** with S = Σ|wᵢ| > 0,
the normalized weighted sum

    ω = Σ wᵢcᵢ / S

satisfies |ω| ≤ 100. After clamping with max(0, min(100, ·)), the output ω ∈ [0, 100].

## Proof

By the triangle inequality:

    |ω| = |Σ wᵢcᵢ| / S
        ≤ Σ |wᵢ| · |cᵢ| / S          (triangle inequality)
        ≤ Σ |wᵢ| · 100 / S            (since cᵢ ∈ [0, 100])
        = 100 · Σ|wᵢ| / S
        = 100                           □

## Minimum bound

The minimum occurs when only the negative-weight component (s_recovery, w = -0.10) is active
at maximum (c = 100) and all other components are 0:

    ω_min = (-0.10 × 100) / 0.99 ≈ -10.1

After clamping: max(0, -10.1) = 0. The clamp is necessary and correct.

## Application

This theorem guarantees that `omega_mem_final` ∈ [0, 100] for any input,
regardless of component values or weight configuration. No input — adversarial
or otherwise — can produce an out-of-range score.

The same bound holds after the action-type and domain multipliers:

    omega_final = min(100, omega × C_action × C_domain)

Since min(100, ·) clamps the upper bound, omega_final ∈ [0, 100] always.

## Verified

- 10,000 random component vectors × random weights: all in [0, 100]
- All 950 corpus cases: all in [0, 100]
- Hand-tuned weights (WEIGHTS dict): satisfies S = 0.99 > 0
