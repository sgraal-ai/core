"""Parallel execution helper for preflight scoring modules.

Usage:
    from api.parallel_exec import run_parallel_safe

    def mod_a(): return compute_a(x)
    def mod_b(): return compute_b(y)
    def mod_c(): return compute_c(z)

    results = run_parallel_safe([mod_a, mod_b, mod_c], timeout=5.0)
    # results = [result_a, result_b, result_c] (same order)
    # Exceptions captured as None; callers should handle that.

Design notes:
- Uses ThreadPoolExecutor. Python's GIL means CPU-bound pure Python sees modest
  parallelism (waiting/I-O is where the win is), but modules that make HTTP calls
  to Redis benefit immediately.
- Preserves order — results[i] corresponds to callables[i].
- Individual module failures are captured; they don't kill the batch.
- A shared lock (`redis_write_lock`) is exposed for modules that must serialize
  Redis writes to avoid races (e.g., incrementing a shared counter).
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Callable, List, Optional, Any


# Shared lock for Redis writes that MUST serialize (shared counters, append-to-list ops)
redis_write_lock = threading.Lock()

# Shared lock for mutating in-memory global state (_metrics, _outcomes, etc.)
# Modules running in parallel must acquire this if they touch shared state.
shared_state_lock = threading.Lock()


# Thread pool sized for typical preflight parallel zones (4-10 modules).
# Reused across calls to avoid thread creation overhead.
_pool_max_workers = 8
_pool: Optional[ThreadPoolExecutor] = None
_pool_lock = threading.Lock()


def _get_pool() -> ThreadPoolExecutor:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ThreadPoolExecutor(max_workers=_pool_max_workers, thread_name_prefix="sgraal-parallel")
    return _pool


def run_parallel_safe(
    callables: List[Callable[[], Any]],
    timeout: float = 5.0,
) -> List[Any]:
    """Run a batch of zero-arg callables concurrently.

    Returns a list of the same length as `callables`. For each slot:
    - the callable's return value on success
    - None on exception or timeout

    Callers inspect results and handle None themselves (graceful degradation).

    This is a drop-in parallel replacement for sequential module invocations
    in preflight scoring. Each callable should be self-contained: read its
    inputs from closure, write its output only via the return value (not
    shared mutable state), and acquire `redis_write_lock` if it writes to
    shared Redis keys.
    """
    if not callables:
        return []
    if len(callables) == 1:
        # Single callable — skip threading overhead entirely
        try:
            return [callables[0]()]
        except Exception:
            return [None]

    pool = _get_pool()
    futures = [pool.submit(fn) for fn in callables]
    results: List[Any] = [None] * len(callables)
    for i, fut in enumerate(futures):
        try:
            results[i] = fut.result(timeout=timeout)
        except (Exception, FuturesTimeoutError):
            results[i] = None
    return results


def shutdown_pool() -> None:
    """Shut down the shared thread pool. Call only on application shutdown."""
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.shutdown(wait=False)
            _pool = None
