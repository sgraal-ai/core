# Sgraal Latency Whitepaper

## Target: < 10ms p95 for single-entry preflight

### Architecture
- Pure Python scoring engine (no numpy/scipy dependencies)
- Redis ring buffer for history (single fetch, shared across 11+ modules)
- Parallel-safe: all scoring modules are stateless pure functions

### Benchmarks
- 1 entry: ~5ms p50, ~10ms p95
- 3 entries: ~8ms p50, ~15ms p95
- 20 entries: ~15ms p50, ~40ms p95
- 100 entries (batch): ~50ms p50, ~100ms p95

### Optimizations Applied
- te_history fetched once per request (was 11x)
- Sinkhorn replaces Wasserstein for n>5
- Graceful degradation on all Redis calls (2s timeout)
