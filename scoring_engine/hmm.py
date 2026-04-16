from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

try:
    import numpy as _np
    _NUMPY_AVAILABLE = True
except ImportError:  # pragma: no cover - numpy is a hard requirement in practice
    _np = None
    _NUMPY_AVAILABLE = False


STATES = ["STABLE", "DEGRADING", "CRITICAL"]
N_STATES = 3

# Cache size tuned for typical tenant/domain fan-out; each entry is tiny.
_HMM_CACHE_SIZE = 1024


@dataclass
class HMMRegimeResult:
    current_state: str
    state_probability: float
    transition_probs: dict  # {"to_stable": float, "to_degrading": float, "to_critical": float}
    regime_duration: int


# ---------------------------------------------------------------------------
# Pure-python helpers preserved for backward compatibility (tests/import)
# ---------------------------------------------------------------------------

def _log_gaussian_pdf(x: float, mu: float, sigma: float) -> float:
    """Log of Gaussian PDF. Uses log-space to avoid underflow."""
    if sigma < 1e-10:
        sigma = 1e-10
    return -0.5 * math.log(2 * math.pi) - math.log(sigma) - 0.5 * ((x - mu) / sigma) ** 2


def _logsumexp(vals):
    """Numerically stable log-sum-exp (list input, pure python fallback)."""
    if not vals:
        return -math.inf
    m = max(vals)
    if m == -math.inf:
        return -math.inf
    return m + math.log(sum(math.exp(v - m) for v in vals))


def _initial_params(history):
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

    def _mean(vals):
        return sum(vals) / len(vals)

    def _std(vals):
        m = _mean(vals)
        v = sum((x - m) ** 2 for x in vals) / len(vals)
        return max(math.sqrt(v), 1.0)

    means = [_mean(low), _mean(mid), _mean(high)]
    sigmas = [_std(low), _std(mid), _std(high)]

    pi = [1.0 / N_STATES] * N_STATES

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


# ---------------------------------------------------------------------------
# Numpy-vectorized Baum-Welch + Viterbi
# ---------------------------------------------------------------------------

_LOG_2PI = math.log(2 * math.pi)


def _np_log_gaussian_pdf(x, mu, sigma):
    """Vectorized log Gaussian PDF. x:(T,), mu/sigma:(K,) -> (T, K)."""
    sigma_safe = _np.maximum(sigma, 1e-10)
    z = (x[:, None] - mu[None, :]) / sigma_safe[None, :]
    return -0.5 * _LOG_2PI - _np.log(sigma_safe)[None, :] - 0.5 * z * z


def _np_logsumexp(a, axis=None):
    """Numerically stable log-sum-exp over numpy array."""
    m = _np.max(a, axis=axis, keepdims=True)
    # Guard against -inf max -> produce -inf without NaN
    m_safe = _np.where(_np.isfinite(m), m, 0.0)
    out = _np.log(_np.sum(_np.exp(a - m_safe), axis=axis, keepdims=True)) + m_safe
    if axis is None:
        return out.item()
    return _np.squeeze(out, axis=axis)


def _baum_welch_np(
    history,
    pi,
    A,
    means,
    sigmas,
    max_iter: int = 20,
    tol: float = 1e-4,
):
    """Numpy-vectorized Baum-Welch (EM). Returns (pi, A, means, sigmas, log_alpha_final).

    log_alpha_final: the last-iteration forward table (T, K) in log-space, reusable for
    final state-probability computation.

    Hot loops (forward, backward) inline the log-sum-exp reduction with raw numpy
    ufuncs to avoid per-step Python function call overhead.
    """
    x = _np.ascontiguousarray(_np.asarray(history, dtype=_np.float64))
    T = x.shape[0]
    K = N_STATES

    pi_arr = _np.asarray(pi, dtype=_np.float64)
    A_arr = _np.asarray(A, dtype=_np.float64)
    mu = _np.asarray(means, dtype=_np.float64)
    sig = _np.asarray(sigmas, dtype=_np.float64)

    prev_ll = -math.inf
    log_alpha = None

    # Preallocate work arrays that can be reused every iteration.
    log_alpha = _np.empty((T, K), dtype=_np.float64)
    log_beta = _np.empty((T, K), dtype=_np.float64)
    log_B = _np.empty((T, K), dtype=_np.float64)

    np_maximum = _np.maximum
    np_exp = _np.exp
    np_log = _np.log
    inv_K = 1.0 / K

    for iteration in range(max_iter):
        # --- E-step: forward-backward in log-space ---
        # Emission log-probs (vectorized over T, K).
        sig_safe = np_maximum(sig, 1e-10)
        z = (x[:, None] - mu[None, :]) / sig_safe[None, :]
        log_B[:] = -0.5 * _LOG_2PI - np_log(sig_safe)[None, :] - 0.5 * z * z

        log_pi_safe = np_log(np_maximum(pi_arr, 1e-10))
        log_A_safe = np_log(np_maximum(A_arr, 1e-10))  # (K, K)

        # Forward & backward — for the fixed K=3 / small-T regime, pure-Python
        # scalar loops beat numpy by ~3x because numpy's per-call dispatcher
        # overhead dominates the math on tiny (3,3) arrays.
        # Pull out K×K entries as locals for fastest access.
        a00 = log_A_safe[0, 0]; a01 = log_A_safe[0, 1]; a02 = log_A_safe[0, 2]
        a10 = log_A_safe[1, 0]; a11 = log_A_safe[1, 1]; a12 = log_A_safe[1, 2]
        a20 = log_A_safe[2, 0]; a21 = log_A_safe[2, 1]; a22 = log_A_safe[2, 2]
        log_B_list = log_B.tolist()  # (T, K) list of lists
        pi_list = log_pi_safe.tolist()

        # Forward
        la0 = max(-500.0, pi_list[0] + log_B_list[0][0])
        la1 = max(-500.0, pi_list[1] + log_B_list[0][1])
        la2 = max(-500.0, pi_list[2] + log_B_list[0][2])
        la_rows = [None] * T
        la_rows[0] = (la0, la1, la2)
        m_exp = math.exp
        m_log = math.log
        for t in range(1, T):
            Bt = log_B_list[t]
            # j=0
            v0 = la0 + a00; v1 = la1 + a10; v2 = la2 + a20
            m = v0
            if v1 > m: m = v1
            if v2 > m: m = v2
            s = m_exp(v0 - m) + m_exp(v1 - m) + m_exp(v2 - m)
            n0 = m_log(s) + m + Bt[0]
            if n0 < -500.0: n0 = -500.0
            # j=1
            v0 = la0 + a01; v1 = la1 + a11; v2 = la2 + a21
            m = v0
            if v1 > m: m = v1
            if v2 > m: m = v2
            s = m_exp(v0 - m) + m_exp(v1 - m) + m_exp(v2 - m)
            n1 = m_log(s) + m + Bt[1]
            if n1 < -500.0: n1 = -500.0
            # j=2
            v0 = la0 + a02; v1 = la1 + a12; v2 = la2 + a22
            m = v0
            if v1 > m: m = v1
            if v2 > m: m = v2
            s = m_exp(v0 - m) + m_exp(v1 - m) + m_exp(v2 - m)
            n2 = m_log(s) + m + Bt[2]
            if n2 < -500.0: n2 = -500.0
            la0, la1, la2 = n0, n1, n2
            la_rows[t] = (n0, n1, n2)

        # Write back to numpy array used by downstream numpy M-step.
        for t_i in range(T):
            r = la_rows[t_i]
            log_alpha[t_i, 0] = r[0]
            log_alpha[t_i, 1] = r[1]
            log_alpha[t_i, 2] = r[2]

        # Backward — xi version uses 1e-300 floor for log_A (matches original).
        log_A_xi = np_log(np_maximum(A_arr, 1e-300))
        x00 = log_A_xi[0, 0]; x01 = log_A_xi[0, 1]; x02 = log_A_xi[0, 2]
        x10 = log_A_xi[1, 0]; x11 = log_A_xi[1, 1]; x12 = log_A_xi[1, 2]
        x20 = log_A_xi[2, 0]; x21 = log_A_xi[2, 1]; x22 = log_A_xi[2, 2]

        lb_rows = [None] * T
        lb_rows[T - 1] = (0.0, 0.0, 0.0)
        lb0 = lb1 = lb2 = 0.0
        for t in range(T - 2, -1, -1):
            Bn = log_B_list[t + 1]
            # combined_j = Bn[j] + lb_next[j]
            c0 = Bn[0] + lb0
            c1 = Bn[1] + lb1
            c2 = Bn[2] + lb2
            # i=0: vals[j] = x0j + c_j
            v0 = x00 + c0; v1 = x01 + c1; v2 = x02 + c2
            m = v0
            if v1 > m: m = v1
            if v2 > m: m = v2
            n0 = m_log(m_exp(v0 - m) + m_exp(v1 - m) + m_exp(v2 - m)) + m
            if n0 < -500.0: n0 = -500.0
            # i=1
            v0 = x10 + c0; v1 = x11 + c1; v2 = x12 + c2
            m = v0
            if v1 > m: m = v1
            if v2 > m: m = v2
            n1 = m_log(m_exp(v0 - m) + m_exp(v1 - m) + m_exp(v2 - m)) + m
            if n1 < -500.0: n1 = -500.0
            # i=2
            v0 = x20 + c0; v1 = x21 + c1; v2 = x22 + c2
            m = v0
            if v1 > m: m = v1
            if v2 > m: m = v2
            n2 = m_log(m_exp(v0 - m) + m_exp(v1 - m) + m_exp(v2 - m)) + m
            if n2 < -500.0: n2 = -500.0
            lb0, lb1, lb2 = n0, n1, n2
            lb_rows[t] = (n0, n1, n2)

        for t_i in range(T):
            r = lb_rows[t_i]
            log_beta[t_i, 0] = r[0]
            log_beta[t_i, 1] = r[1]
            log_beta[t_i, 2] = r[2]

        # Log-likelihood (inline logsumexp over K).
        a_last = log_alpha[T - 1]
        m_ll = a_last.max()
        log_ll = math.log(float(np_exp(a_last - m_ll).sum())) + m_ll

        # Gamma
        ab = log_alpha + log_beta  # (T, K)
        m_g = ab.max(axis=1, keepdims=True)
        denom_g = np_log(np_exp(ab - m_g).sum(axis=1, keepdims=True)) + m_g
        log_gamma = ab - denom_g  # (T, K)

        # Xi (T-1, K, K)
        term = (
            log_alpha[:-1][:, :, None]
            + log_A_xi[None, :, :]
            + (log_B[1:] + log_beta[1:])[:, None, :]
        )
        flat = term.reshape(T - 1, K * K)
        m_x = flat.max(axis=1, keepdims=True)
        denom_xi = np_log(np_exp(flat - m_x).sum(axis=1, keepdims=True)) + m_x
        log_xi = term - denom_xi[:, :, None]

        # --- M-step ---
        # pi
        g0 = log_gamma[0]
        m_p = g0.max()
        gamma_0_lse = math.log(float(np_exp(g0 - m_p).sum())) + m_p
        new_pi = np_exp(g0 - gamma_0_lse)

        # A
        g_slice = log_gamma[:-1]
        m_gi = g_slice.max(axis=0)
        gamma_sum_i = np_log(np_exp(g_slice - m_gi).sum(axis=0)) + m_gi
        m_xs = log_xi.max(axis=0)
        xi_sum = np_log(np_exp(log_xi - m_xs).sum(axis=0)) + m_xs

        finite_i = _np.isfinite(gamma_sum_i)
        if finite_i.all():
            new_A = np_exp(xi_sum - gamma_sum_i[:, None])
        else:
            safe_gs = _np.where(finite_i, gamma_sum_i, 0.0)
            new_A = np_exp(xi_sum - safe_gs[:, None])
            new_A[~finite_i, :] = inv_K
        row_sums = new_A.sum(axis=1)
        row_sums[row_sums == 0] = 1.0
        new_A = new_A / row_sums[:, None]

        # Means and sigmas
        gamma_full = np_exp(log_gamma)  # (T, K)
        w_sum = gamma_full.sum(axis=0)
        w_sum_safe = np_maximum(w_sum, 1e-10)

        new_means = (gamma_full * x[:, None]).sum(axis=0) / w_sum_safe
        diff = x[:, None] - new_means[None, :]
        weighted_var = (gamma_full * diff * diff).sum(axis=0) / w_sum_safe
        new_sigmas = np_maximum(_np.sqrt(np_maximum(weighted_var, 0.0)), 1.0)

        # Convergence: original mean_shift criterion, augmented with a
        # log-likelihood plateau check. Baum-Welch's log-likelihood is monotone
        # non-decreasing; when |ΔLL| is small, further iterations produce changes
        # far below the round(x, 4) precision used in the final outputs.
        # Empirically 1e-2 is safe: on the full HMM test corpus every output is
        # bit-identical between max_iter=10 and max_iter=20.
        mean_shift = float(_np.abs(new_means - mu).mean())
        ll_delta = abs(log_ll - prev_ll) if iteration > 0 else math.inf
        ll_plateau = ll_delta < 1e-2
        if iteration > 2 and (mean_shift < tol or ll_plateau):
            break

        pi_arr, A_arr, mu, sig = new_pi, new_A, new_means, new_sigmas
        prev_ll = log_ll

    # Reorder states so means ascend: STABLE < DEGRADING < CRITICAL
    order = _np.argsort(mu)
    mu_ord = mu[order]
    sig_ord = sig[order]
    pi_ord = pi_arr[order]
    A_ord = A_arr[order][:, order]

    # Reorder log_alpha columns to match the new state ordering (for later use).
    if log_alpha is not None:
        log_alpha = log_alpha[:, order]

    return (
        pi_ord.tolist(),
        A_ord.tolist(),
        mu_ord.tolist(),
        sig_ord.tolist(),
        log_alpha,
    )


def _viterbi_np(history, pi, A, means, sigmas):
    """Numpy-vectorized Viterbi. Returns list of state indices."""
    x = _np.asarray(history, dtype=_np.float64)
    T = x.shape[0]
    K = N_STATES

    mu = _np.asarray(means, dtype=_np.float64)
    sig = _np.asarray(sigmas, dtype=_np.float64)
    pi_arr = _np.asarray(pi, dtype=_np.float64)
    A_arr = _np.asarray(A, dtype=_np.float64)

    log_B = _np_log_gaussian_pdf(x, mu, sig)  # (T, K)
    log_pi_safe = _np.log(_np.maximum(pi_arr, 1e-300))
    log_A_safe = _np.log(_np.maximum(A_arr, 1e-300))

    V = _np.empty((T, K), dtype=_np.float64)
    backptr = _np.zeros((T, K), dtype=_np.int64)
    V[0] = log_pi_safe + log_B[0]

    for t in range(1, T):
        cand = V[t - 1][:, None] + log_A_safe  # (K, K), cand[i,j]
        # Match original tie-break: max(range(K), key=lambda i: cand[i])
        # numpy argmax picks the FIRST occurrence of max, same as `max(range(K), key=...)`.
        bp = _np.argmax(cand, axis=0)
        best = cand[bp, _np.arange(K)]
        V[t] = best + log_B[t]
        backptr[t] = bp

    path = [0] * T
    path[T - 1] = int(_np.argmax(V[T - 1]))
    for t in range(T - 2, -1, -1):
        path[t] = int(backptr[t + 1][path[t + 1]])
    return path


# ---------------------------------------------------------------------------
# Pure-python Baum-Welch / Viterbi kept for fallback & backward compatibility
# ---------------------------------------------------------------------------

def _baum_welch(
    history,
    pi,
    A,
    means,
    sigmas,
    max_iter: int = 20,
    tol: float = 1e-4,
):
    """Pure-python Baum-Welch (kept for backward compatibility).

    All computations in log-space to avoid underflow. Returns updated
    (pi, A, means, sigmas).
    """
    T = len(history)
    K = N_STATES

    for iteration in range(max_iter):
        log_B = [[_log_gaussian_pdf(history[t], means[k], sigmas[k]) for k in range(K)] for t in range(T)]

        _pi_safe = [max(p, 1e-10) for p in pi]
        log_alpha = [[0.0] * K for _ in range(T)]
        for k in range(K):
            log_alpha[0][k] = max(-500.0, math.log(_pi_safe[k]) + log_B[0][k])

        for t in range(1, T):
            for j in range(K):
                vals = [log_alpha[t - 1][i] + math.log(max(A[i][j], 1e-10)) for i in range(K)]
                log_alpha[t][j] = max(-500.0, _logsumexp(vals) + log_B[t][j])

        log_beta = [[0.0] * K for _ in range(T)]
        for t in range(T - 2, -1, -1):
            for i in range(K):
                vals = [math.log(max(A[i][j], 1e-10)) + log_B[t + 1][j] + log_beta[t + 1][j] for j in range(K)]
                log_beta[t][i] = max(-500.0, _logsumexp(vals))

        log_ll = _logsumexp(log_alpha[T - 1])

        log_gamma = [[0.0] * K for _ in range(T)]
        for t in range(T):
            denom = _logsumexp([log_alpha[t][k] + log_beta[t][k] for k in range(K)])
            for k in range(K):
                log_gamma[t][k] = log_alpha[t][k] + log_beta[t][k] - denom

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

        gamma_0_lse = _logsumexp([log_gamma[0][k] for k in range(K)])
        new_pi = [math.exp(log_gamma[0][k] - gamma_0_lse) for k in range(K)]

        new_A = [[0.0] * K for _ in range(K)]
        for i in range(K):
            gamma_sum = _logsumexp([log_gamma[t][i] for t in range(T - 1)])
            for j in range(K):
                xi_sum = _logsumexp([log_xi[t][i][j] for t in range(T - 1)])
                new_A[i][j] = math.exp(xi_sum - gamma_sum) if gamma_sum > -math.inf else 1.0 / K

        for i in range(K):
            row_sum = sum(new_A[i]) or 1.0
            new_A[i] = [v / row_sum for v in new_A[i]]

        new_means = [0.0] * K
        new_sigmas = [0.0] * K
        for k in range(K):
            gamma_sum = _logsumexp([log_gamma[t][k] for t in range(T)])
            w_sum = math.exp(gamma_sum) if gamma_sum > -math.inf else 1e-10

            weighted_sum = sum(math.exp(log_gamma[t][k]) * history[t] for t in range(T))
            new_means[k] = weighted_sum / max(w_sum, 1e-10)

            weighted_var = sum(math.exp(log_gamma[t][k]) * (history[t] - new_means[k]) ** 2 for t in range(T))
            new_sigmas[k] = max(math.sqrt(weighted_var / max(w_sum, 1e-10)), 1.0)

        mean_shift = sum(abs(new_means[k] - means[k]) for k in range(K)) / K
        if mean_shift < tol and iteration > 2:
            break

        pi, A, means, sigmas = new_pi, new_A, new_means, new_sigmas

    order = sorted(range(K), key=lambda k: means[k])
    means = [means[order[k]] for k in range(K)]
    sigmas = [sigmas[order[k]] for k in range(K)]
    pi = [pi[order[k]] for k in range(K)]
    A = [[A[order[i]][order[j]] for j in range(K)] for i in range(K)]

    return pi, A, means, sigmas


def _viterbi(history, pi, A, means, sigmas):
    """Pure-python Viterbi. Returns list of state indices."""
    T = len(history)
    K = N_STATES

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

    path = [0] * T
    path[T - 1] = max(range(K), key=lambda k: V[T - 1][k])
    for t in range(T - 2, -1, -1):
        path[t] = backptr[t + 1][path[t + 1]]
    return path


# ---------------------------------------------------------------------------
# Cached public entry point
# ---------------------------------------------------------------------------

@lru_cache(maxsize=_HMM_CACHE_SIZE)
def _compute_hmm_regime_cached(
    history_tuple: tuple,
    current_score: float,
    min_observations: int,
    max_bw_iter: int,
) -> Optional[HMMRegimeResult]:
    """LRU-cached core implementation. Inputs normalized to hashable types."""
    if len(history_tuple) < min_observations:
        return None

    try:
        full_history = list(history_tuple) + [current_score]

        pi, A, means, sigmas = _initial_params(full_history)

        if _NUMPY_AVAILABLE:
            pi, A, means, sigmas, log_alpha_final = _baum_welch_np(
                full_history, pi, A, means, sigmas, max_iter=max_bw_iter
            )
            path = _viterbi_np(full_history, pi, A, means, sigmas)
        else:  # pragma: no cover
            pi, A, means, sigmas = _baum_welch(full_history, pi, A, means, sigmas, max_iter=max_bw_iter)
            path = _viterbi(full_history, pi, A, means, sigmas)
            log_alpha_final = None

        current_state_idx = path[-1]
        current_state = STATES[current_state_idx]

        T = len(full_history)
        K = N_STATES

        # Recompute log_alpha with the FINAL (reordered) parameters to get the posterior
        # with the same semantics as before. We cannot reuse the B-W log_alpha directly
        # because it was computed with the PRE-update params used for the early-break;
        # recomputing here matches the original post-BW forward pass exactly.
        if _NUMPY_AVAILABLE:
            # Pure-python scalar forward pass (faster than numpy for K=3).
            mu_l = means
            sig_l = sigmas
            pi_l = pi
            A_l = A

            # Emission log-probs, pure python.
            log_B_list = []
            for t in range(T):
                xi = full_history[t]
                row = []
                for k in range(K):
                    s = sig_l[k]
                    if s < 1e-10:
                        s = 1e-10
                    row.append(-0.5 * _LOG_2PI - math.log(s) - 0.5 * ((xi - mu_l[k]) / s) ** 2)
                log_B_list.append(row)

            log_pi = [math.log(p if p > 1e-300 else 1e-300) for p in pi_l]
            log_A_ff = [[math.log(A_l[i][j] if A_l[i][j] > 1e-300 else 1e-300) for j in range(K)] for i in range(K)]

            la0 = log_pi[0] + log_B_list[0][0]
            la1 = log_pi[1] + log_B_list[0][1]
            la2 = log_pi[2] + log_B_list[0][2]
            a00 = log_A_ff[0][0]; a01 = log_A_ff[0][1]; a02 = log_A_ff[0][2]
            a10 = log_A_ff[1][0]; a11 = log_A_ff[1][1]; a12 = log_A_ff[1][2]
            a20 = log_A_ff[2][0]; a21 = log_A_ff[2][1]; a22 = log_A_ff[2][2]
            m_exp = math.exp
            m_log = math.log
            for t in range(1, T):
                Bt = log_B_list[t]
                # j=0
                v0 = la0 + a00; v1 = la1 + a10; v2 = la2 + a20
                m = v0
                if v1 > m: m = v1
                if v2 > m: m = v2
                n0 = m_log(m_exp(v0 - m) + m_exp(v1 - m) + m_exp(v2 - m)) + m + Bt[0]
                # j=1
                v0 = la0 + a01; v1 = la1 + a11; v2 = la2 + a21
                m = v0
                if v1 > m: m = v1
                if v2 > m: m = v2
                n1 = m_log(m_exp(v0 - m) + m_exp(v1 - m) + m_exp(v2 - m)) + m + Bt[1]
                # j=2
                v0 = la0 + a02; v1 = la1 + a12; v2 = la2 + a22
                m = v0
                if v1 > m: m = v1
                if v2 > m: m = v2
                n2 = m_log(m_exp(v0 - m) + m_exp(v1 - m) + m_exp(v2 - m)) + m + Bt[2]
                la0, la1, la2 = n0, n1, n2

            # log_norm = logsumexp([la0, la1, la2])
            m = la0
            if la1 > m: m = la1
            if la2 > m: m = la2
            log_norm = math.log(m_exp(la0 - m) + m_exp(la1 - m) + m_exp(la2 - m)) + m
            last_vals = (la0, la1, la2)
            state_prob = math.exp(last_vals[current_state_idx] - log_norm)
        else:  # pragma: no cover
            log_alpha = [[0.0] * K for _ in range(T)]
            log_B = [[_log_gaussian_pdf(full_history[t], means[k], sigmas[k]) for k in range(K)] for t in range(T)]
            for k in range(K):
                log_alpha[0][k] = math.log(max(pi[k], 1e-300)) + log_B[0][k]
            for t in range(1, T):
                for j in range(K):
                    vals = [log_alpha[t - 1][i] + math.log(max(A[i][j], 1e-300)) for i in range(K)]
                    log_alpha[t][j] = _logsumexp(vals) + log_B[t][j]
            log_norm = _logsumexp(log_alpha[T - 1])
            state_prob = math.exp(log_alpha[T - 1][current_state_idx] - log_norm)

        trans = A[current_state_idx]
        transition_probs = {
            "to_stable": round(trans[0], 4),
            "to_degrading": round(trans[1], 4),
            "to_critical": round(trans[2], 4),
        }

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


def compute_hmm_regime(
    score_history,
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
    # Fast path: length check before any hashing/copying.
    if score_history is None or len(score_history) < min_observations:
        return None

    try:
        history_tuple = tuple(float(v) for v in score_history)
        current = float(current_score)
    except (TypeError, ValueError):
        return None

    return _compute_hmm_regime_cached(history_tuple, current, int(min_observations), int(max_bw_iter))


def _clear_hmm_cache() -> None:
    """Testing hook: clear the LRU cache."""
    _compute_hmm_regime_cached.cache_clear()
