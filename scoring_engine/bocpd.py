from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class BOCPDResult:
    p_changepoint: float
    regime_change: bool
    current_run_length: int
    merkle_reset_triggered: bool


class BOCPDetector:
    """Bayesian Online Change Point Detection.

    P(rₜ|x_{1:t}) ∝ P(rₜ|x_{1:t-1}) · P(xₜ|rₜ) · H(rₜ)

    Uses Gaussian likelihood with online mean/variance estimation.
    H = hazard rate = prior probability of changepoint per step.
    """

    def __init__(self, hazard_rate: float = 0.01, changepoint_threshold: float = 0.9):
        self.hazard = hazard_rate
        self.threshold = changepoint_threshold

    def detect(self, history: list[float]) -> BOCPDResult:
        """Run BOCPD on a sequence of omega_mem_final scores.

        Args:
            history: list of scores over time

        Returns:
            BOCPDResult with changepoint probability, regime detection,
            run length, and merkle reset flag
        """
        n = len(history)

        if n < 3:
            return BOCPDResult(
                p_changepoint=0.0,
                regime_change=False,
                current_run_length=n,
                merkle_reset_triggered=False,
            )

        # Run length distribution: R[t] = probability that current run has length t
        # Initialize: P(r=0) = 1 at start
        max_run = n + 1
        R = [0.0] * max_run
        R[0] = 1.0

        # Online sufficient statistics per run length
        # For Gaussian: track count, sum, sum_sq
        counts = [0.0] * max_run
        sums = [0.0] * max_run
        sum_sqs = [0.0] * max_run

        # Prior parameters for Gaussian
        mu0 = 50.0      # prior mean
        kappa0 = 1.0     # prior precision weight
        alpha0 = 1.0     # prior shape
        beta0 = 400.0    # prior scale (variance ~ 20²)

        max_p_change = 0.0
        current_run = 0

        for t in range(n):
            x = history[t]

            # Compute predictive probability P(xₜ|run_length=r) for each r
            # Using Student-t posterior predictive
            pred_probs = [0.0] * max_run
            for r in range(min(t + 1, max_run)):
                if R[r] < 1e-20:
                    continue

                kappa_n = kappa0 + counts[r]
                mu_n = (kappa0 * mu0 + sums[r]) / kappa_n if kappa_n > 0 else mu0
                alpha_n = alpha0 + counts[r] / 2.0
                beta_n = beta0 + 0.5 * (sum_sqs[r] - sums[r] ** 2 / max(counts[r], 1e-10)) if counts[r] > 1 else beta0
                beta_n += kappa0 * counts[r] * (sums[r] / max(counts[r], 1e-10) - mu0) ** 2 / (2.0 * kappa_n) if counts[r] > 0 else 0

                # Student-t predictive: approximate with Gaussian for speed
                pred_var = beta_n * (kappa_n + 1) / (alpha_n * kappa_n) if alpha_n > 0 and kappa_n > 0 else 400.0
                pred_var = max(pred_var, 1.0)
                pred_std = math.sqrt(pred_var)

                # Gaussian predictive probability
                z = (x - mu_n) / pred_std
                pred_probs[r] = math.exp(-0.5 * z * z) / (pred_std * math.sqrt(2 * math.pi))

            # Growth probabilities: P(r_{t+1} = r+1)
            new_R = [0.0] * max_run
            for r in range(min(t + 1, max_run - 1)):
                new_R[r + 1] = R[r] * pred_probs[r] * (1 - self.hazard)

            # Changepoint probability: P(r_{t+1} = 0)
            cp_mass = sum(R[r] * pred_probs[r] * self.hazard for r in range(min(t + 1, max_run)))

            new_R[0] = cp_mass

            # Normalize
            total = sum(new_R)
            if total > 1e-20:
                new_R = [r / total for r in new_R]

            R = new_R

            # Update sufficient statistics
            new_counts = [0.0] * max_run
            new_sums = [0.0] * max_run
            new_sum_sqs = [0.0] * max_run

            # Run length 0: reset stats
            new_counts[0] = 0
            new_sums[0] = 0
            new_sum_sqs[0] = 0

            for r in range(min(t + 1, max_run - 1)):
                new_counts[r + 1] = counts[r] + 1
                new_sums[r + 1] = sums[r] + x
                new_sum_sqs[r + 1] = sum_sqs[r] + x * x

            counts = new_counts
            sums = new_sums
            sum_sqs = new_sum_sqs

            # Track changepoint probability and run length
            max_p_change = max(max_p_change, R[0])

        # Current run length: argmax of R
        current_run = max(range(len(R)), key=lambda i: R[i])

        # Final changepoint probability: P(r=0) at last step
        p_cp = round(R[0], 4)
        regime_change = p_cp > self.threshold
        merkle_reset = regime_change  # trigger Merkle reset on regime change

        return BOCPDResult(
            p_changepoint=p_cp,
            regime_change=regime_change,
            current_run_length=current_run,
            merkle_reset_triggered=merkle_reset,
        )


def compute_bocpd(
    history: list[float],
    hazard_rate: float = 0.01,
    threshold: float = 0.9,
) -> BOCPDResult:
    """Convenience function for BOCPD computation."""
    detector = BOCPDetector(hazard_rate=hazard_rate, changepoint_threshold=threshold)
    return detector.detect(history)
