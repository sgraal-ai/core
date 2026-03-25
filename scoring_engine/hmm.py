from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


STATES = ["STABLE", "DEGRADING", "CRITICAL"]
N_STATES = 3


@dataclass
class HMMRegimeResult:
    current_state: str
    state_probability: float
    transition_probs: dict  # {"to_stable": float, "to_degrading": float, "to_critical": float}
    regime_duration: int


def _log_gaussian_pdf(x: float, mu: float, sigma: float) -> float:
    """Log of Gaussian PDF. Uses log-space to avoid underflow."""
    if sigma < 1e-10:
        sigma = 1e-10
    return -0.5 * math.log(2 * math.pi) - math.log(sigma) - 0.5 * ((x - mu) / sigma) ** 2


def _logsumexp(vals: list[float]) -> float:
    """Numerically stable log-sum-exp."""
    if not vals:
        return -math.inf
    m = max(vals)
    if m == -math.inf:
        return -math.inf
    return m + math.log(sum(math.exp(v - m) for v in vals))


def _initial_params(history: list[float]) -> tuple:
    """Initialize HMM parameters from data heuristics.

    Returns (pi, A, means, sigmas) where:
        pi: initial state distribution [3]
        A: transition matrix [3][3]
        means: emission means [3]
        sigmas: emission stds [3]
    """
    sorted_h = sorted(history)
    n = len(sorted_h)

    # Split data into terciles for initial emission parameters
    t1 = n // 3
    t2 = 2 * n // 3
    low = sorted_h[:t1] if t1 > 0 else sorted_h[:1]
    mid = sorted_h[t1:t2] if t2 > t1 else sorted_h[:1]
    high = sorted_h[t2:] if t2 < n else sorted_h[-1:]

    def _mean(vals: list[float]) -> float:
        return sum(vals) / len(vals)

    def _std(vals: list[float]) -> float:
        m = _mean(vals)
        v = sum((x - m) ** 2 for x in vals) / len(vals)
        return max(math.sqrt(v), 1.0)

    # STABLE = low omega (good), DEGRADING = mid, CRITICAL = high omega (bad)
    means = [_mean(low), _mean(mid), _mean(high)]
    sigmas = [_std(low), _std(mid), _std(high)]

    # Initial state distribution: uniform
    pi = [1.0 / N_STATES] * N_STATES

    # Transition matrix: favor staying in current state
    A = [[0.0] * N_STATES for _ in range(N_STATES)]
    for i in range(N_STATES):
        for j in range(N_STATES):
            if i == j:
                A[i][j] = 0.7
            elif abs(i - j) == 1:
                A[i][j] = 0.2
            else:
                A[i][j] = 0.1

    return pi, A, means, sigmas


def _baum_welch(
    history: list[float],
    pi: list[float],
    A: list[list[float]],
    means: list[float],
    sigmas: list[float],
    max_iter: int = 20,
    tol: float = 1e-4,
) -> tuple:
    """Baum-Welch (EM) algorithm for HMM parameter estimation.

    All computations in log-space to avoid underflow.

    Returns updated (pi, A, means, sigmas).
    """
    T = len(history)
    K = N_STATES

    for iteration in range(max_iter):
        # --- E-step: forward-backward in log-space ---

        # Log emission probabilities: log_B[t][k]
        log_B = [[_log_gaussian_pdf(history[t], means[k], sigmas[k]) for k in range(K)] for t in range(T)]

        # Forward: log_alpha[t][k]
        log_alpha = [[0.0] * K for _ in range(T)]
        for k in range(K):
            log_alpha[0][k] = math.log(max(pi[k], 1e-300)) + log_B[0][k]

        for t in range(1, T):
            for j in range(K):
                vals = [log_alpha[t - 1][i] + math.log(max(A[i][j], 1e-300)) for i in range(K)]
                log_alpha[t][j] = _logsumexp(vals) + log_B[t][j]

        # Backward: log_beta[t][k]
        log_beta = [[0.0] * K for _ in range(T)]
        # log_beta[T-1][k] = 0 (log(1))

        for t in range(T - 2, -1, -1):
            for i in range(K):
                vals = [math.log(max(A[i][j], 1e-300)) + log_B[t + 1][j] + log_beta[t + 1][j] for j in range(K)]
                log_beta[t][i] = _logsumexp(vals)

        # Log-likelihood
        log_ll = _logsumexp(log_alpha[T - 1])

        # Posterior: log_gamma[t][k] = log P(state=k at t | observations)
        log_gamma = [[0.0] * K for _ in range(T)]
        for t in range(T):
            denom = _logsumexp([log_alpha[t][k] + log_beta[t][k] for k in range(K)])
            for k in range(K):
                log_gamma[t][k] = log_alpha[t][k] + log_beta[t][k] - denom

        # Xi: log P(state=i at t, state=j at t+1 | obs)
        # log_xi[t][i][j]
        log_xi = [[[0.0] * K for _ in range(K)] for _ in range(T - 1)]
        for t in range(T - 1):
            denom_vals = []
            for i in range(K):
                for j in range(K):
                    v = log_alpha[t][i] + math.log(max(A[i][j], 1e-300)) + log_B[t + 1][j] + log_beta[t + 1][j]
                    denom_vals.append(v)
            denom = _logsumexp(denom_vals)

            for i in range(K):
                for j in range(K):
                    log_xi[t][i][j] = (
                        log_alpha[t][i] + math.log(max(A[i][j], 1e-300)) + log_B[t + 1][j] + log_beta[t + 1][j] - denom
                    )

        # --- M-step ---

        # Update pi
        gamma_0_lse = _logsumexp([log_gamma[0][k] for k in range(K)])
        new_pi = [math.exp(log_gamma[0][k] - gamma_0_lse) for k in range(K)]

        # Update A
        new_A = [[0.0] * K for _ in range(K)]
        for i in range(K):
            gamma_sum = _logsumexp([log_gamma[t][i] for t in range(T - 1)])
            for j in range(K):
                xi_sum = _logsumexp([log_xi[t][i][j] for t in range(T - 1)])
                new_A[i][j] = math.exp(xi_sum - gamma_sum) if gamma_sum > -math.inf else 1.0 / K

        # Normalize rows
        for i in range(K):
            row_sum = sum(new_A[i]) or 1.0
            new_A[i] = [v / row_sum for v in new_A[i]]

        # Update means and sigmas
        new_means = [0.0] * K
        new_sigmas = [0.0] * K
        for k in range(K):
            gamma_sum = _logsumexp([log_gamma[t][k] for t in range(T)])
            w_sum = math.exp(gamma_sum) if gamma_sum > -math.inf else 1e-10

            # Weighted mean
            weighted_sum = sum(math.exp(log_gamma[t][k]) * history[t] for t in range(T))
            new_means[k] = weighted_sum / max(w_sum, 1e-10)

            # Weighted variance
            weighted_var = sum(math.exp(log_gamma[t][k]) * (history[t] - new_means[k]) ** 2 for t in range(T))
            new_sigmas[k] = max(math.sqrt(weighted_var / max(w_sum, 1e-10)), 1.0)

        # Check convergence
        mean_shift = sum(abs(new_means[k] - means[k]) for k in range(K)) / K
        if mean_shift < tol and iteration > 2:
            break

        pi, A, means, sigmas = new_pi, new_A, new_means, new_sigmas

    # Ensure means are ordered: STABLE < DEGRADING < CRITICAL
    order = sorted(range(K), key=lambda k: means[k])
    means = [means[order[k]] for k in range(K)]
    sigmas = [sigmas[order[k]] for k in range(K)]
    pi = [pi[order[k]] for k in range(K)]
    A = [[A[order[i]][order[j]] for j in range(K)] for i in range(K)]

    return pi, A, means, sigmas


def _viterbi(
    history: list[float],
    pi: list[float],
    A: list[list[float]],
    means: list[float],
    sigmas: list[float],
) -> list[int]:
    """Viterbi algorithm for most likely state sequence.

    Returns list of state indices.
    """
    T = len(history)
    K = N_STATES

    # Log-space Viterbi
    V = [[0.0] * K for _ in range(T)]
    backptr = [[0] * K for _ in range(T)]

    for k in range(K):
        V[0][k] = math.log(max(pi[k], 1e-300)) + _log_gaussian_pdf(history[0], means[k], sigmas[k])

    for t in range(1, T):
        for j in range(K):
            candidates = [V[t - 1][i] + math.log(max(A[i][j], 1e-300)) for i in range(K)]
            best_i = max(range(K), key=lambda i: candidates[i])
            V[t][j] = candidates[best_i] + _log_gaussian_pdf(history[t], means[j], sigmas[j])
            backptr[t][j] = best_i

    # Backtrace
    path = [0] * T
    path[T - 1] = max(range(K), key=lambda k: V[T - 1][k])
    for t in range(T - 2, -1, -1):
        path[t] = backptr[t + 1][path[t + 1]]

    return path


def compute_hmm_regime(
    score_history: list[float],
    current_score: float,
    min_observations: int = 20,
    max_bw_iter: int = 20,
) -> Optional[HMMRegimeResult]:
    """Classify memory regime via 3-state Hidden Markov Model.

    States: STABLE (low omega), DEGRADING (mid), CRITICAL (high).
    Uses Baum-Welch for parameter estimation, Viterbi for decoding.

    Args:
        score_history: past omega_mem_final scores (oldest first)
        current_score: current omega_mem_final score
        min_observations: minimum history length (default 20)
        max_bw_iter: max Baum-Welch iterations (default 20)

    Returns:
        HMMRegimeResult or None if insufficient history
    """
    if len(score_history) < min_observations:
        return None

    try:
        full_history = score_history + [current_score]

        # Initialize and run Baum-Welch
        pi, A, means, sigmas = _initial_params(full_history)
        pi, A, means, sigmas = _baum_welch(full_history, pi, A, means, sigmas, max_iter=max_bw_iter)

        # Viterbi decoding
        path = _viterbi(full_history, pi, A, means, sigmas)

        # Current state
        current_state_idx = path[-1]
        current_state = STATES[current_state_idx]

        # State probability from forward algorithm (last step)
        T = len(full_history)
        K = N_STATES
        log_alpha = [[0.0] * K for _ in range(T)]
        log_B = [[_log_gaussian_pdf(full_history[t], means[k], sigmas[k]) for k in range(K)] for t in range(T)]

        for k in range(K):
            log_alpha[0][k] = math.log(max(pi[k], 1e-300)) + log_B[0][k]
        for t in range(1, T):
            for j in range(K):
                vals = [log_alpha[t - 1][i] + math.log(max(A[i][j], 1e-300)) for i in range(K)]
                log_alpha[t][j] = _logsumexp(vals) + log_B[t][j]

        # P(state=k at T | obs) ∝ alpha[T][k]
        log_norm = _logsumexp(log_alpha[T - 1])
        state_prob = math.exp(log_alpha[T - 1][current_state_idx] - log_norm)

        # Transition probabilities from current state
        trans = A[current_state_idx]
        transition_probs = {
            "to_stable": round(trans[0], 4),
            "to_degrading": round(trans[1], 4),
            "to_critical": round(trans[2], 4),
        }

        # Regime duration: count consecutive same-state steps from end
        regime_duration = 1
        for t in range(len(path) - 2, -1, -1):
            if path[t] == current_state_idx:
                regime_duration += 1
            else:
                break

        return HMMRegimeResult(
            current_state=current_state,
            state_probability=round(state_prob, 4),
            transition_probs=transition_probs,
            regime_duration=regime_duration,
        )
    except Exception:
        return None
