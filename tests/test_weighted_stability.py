"""Test T2: Weighted StabilityScore.

Verify that use_temperature_weights=True produces a different (temperature-aware)
score than the default equal-weighted formula for asymmetric component vectors.
"""
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring_engine.stability_score import compute_stability_score


class TestWeightedStabilityScore:
    def test_weighted_differs_from_unweighted_for_asymmetric_components(self):
        """When only low-weight axis components are elevated, weighted score differs from unweighted.

        If we push h1_rank (PC4, weight 0.055) to a high value but keep Trust-axis
        components (PC1, weight 0.574) clean, the weighted score should not collapse
        as much as the unweighted score — because the frozen/low-weight axis
        contributes less to instability.
        """
        # Only h1_rank (low-weight PC4) is bad; Trust-axis components are clean
        unweighted = compute_stability_score(
            delta_alpha=0.0, p_transition=0.0, omega_drift=0.0, omega_0=0.0,
            lambda_2=0.0, hurst=0.0, h1_rank=10.0, tau_mix=0.0, d_geo_causal=0.0,
            use_temperature_weights=False,
        )
        weighted = compute_stability_score(
            delta_alpha=0.0, p_transition=0.0, omega_drift=0.0, omega_0=0.0,
            lambda_2=0.0, hurst=0.0, h1_rank=10.0, tau_mix=0.0, d_geo_causal=0.0,
            use_temperature_weights=True,
        )
        # Both scores valid
        assert 0.0 <= unweighted.score <= 1.0
        assert 0.0 <= weighted.score <= 1.0
        # They must differ — weighted gives less importance to h1_rank (PC4 axis)
        assert unweighted.score != weighted.score
        # Weighted should be HIGHER (less penalty for low-weight-axis instability)
        assert weighted.score > unweighted.score

    def test_weighted_and_unweighted_agree_when_all_clean(self):
        """If all components are at minimum, both should give score ≈ 1.0."""
        unweighted = compute_stability_score(use_temperature_weights=False)
        weighted = compute_stability_score(use_temperature_weights=True)
        assert unweighted.score > 0.95
        assert weighted.score > 0.95

    def test_weighted_defaults_to_equal_weights(self):
        """Omitting use_temperature_weights preserves the original equal-weight formula."""
        default = compute_stability_score(
            delta_alpha=1.0, p_transition=0.5, omega_drift=0.3,
            omega_0=0.4, lambda_2=2.0, hurst=0.5,
            h1_rank=3.0, tau_mix=20.0, d_geo_causal=0.5,
        )
        explicit_unweighted = compute_stability_score(
            delta_alpha=1.0, p_transition=0.5, omega_drift=0.3,
            omega_0=0.4, lambda_2=2.0, hurst=0.5,
            h1_rank=3.0, tau_mix=20.0, d_geo_causal=0.5,
            use_temperature_weights=False,
        )
        # Same input, default weighting = no weights
        assert default.score == explicit_unweighted.score

    def test_weighted_emphasizes_trust_axis(self):
        """Penalty on Trust-axis components (delta_alpha) reduces weighted score more than on low-weight axes."""
        # Bad Trust-axis: delta_alpha at max
        trust_bad = compute_stability_score(
            delta_alpha=2.0, p_transition=0.0, omega_drift=0.0, omega_0=0.0,
            lambda_2=0.0, hurst=0.0, h1_rank=0.0, tau_mix=0.0, d_geo_causal=0.0,
            use_temperature_weights=True,
        )
        # Bad low-weight axis: d_geo_causal at max
        lowaxis_bad = compute_stability_score(
            delta_alpha=0.0, p_transition=0.0, omega_drift=0.0, omega_0=0.0,
            lambda_2=0.0, hurst=0.0, h1_rank=0.0, tau_mix=0.0, d_geo_causal=2.0,
            use_temperature_weights=True,
        )
        # Trust-axis damage should lower the score MORE than low-axis damage
        assert trust_bad.score < lowaxis_bad.score
