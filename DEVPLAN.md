# Sgraal Development Plan

## Sprint — 2026-03-23

### Completed Tasks

| Task | Description | Status | Tests |
|------|-------------|--------|-------|
| T-08 | Healing counter + idempotent policy + A2 axiom | Done | 8 tests |
| T-09 | Global State Vector (GSV) via Upstash Redis | Done | 7 tests |
| T-10 | OPA compliance engine — EU AI Act, FDA 510K, HIPAA | Done | 11 tests |
| T-11 | Decision Readiness Dashboard (app.sgraal.com) | Done | mock data |
| T-12 | Live API connection for dashboard (Settings panel, demo fleet) | Done | — |
| T-13 | 4-signal importance detector + at-risk warnings | Done | 9 tests |
| T-14 | Outcome Registry + shadow calibration stub | Done | 6 tests |
| T-15 | Client optimizer (refactored from GrokGuard — generic for any client) | Done | 4 tests |
| T-16 | Kalman filter trend forecasting for Ω_MEM scores | Done | 8 tests |
| T-17 | Z3 SMT formal verification layer | Done | 9 tests |
| T-18 | Memory Dependency Graph — surgical BLOCK | Done | 8 tests |
| T-19 | Automatic memory access tracking + SDK StepTracker | Done | 9 tests |
| T-20 | Memory Privacy Layer — 3-layer protection (obfuscation, abstraction, ZK) | Done | 13 tests |
| T-21 | Thread-aware scaling — bucketing + adaptive sampling | Done | 7 tests |
| T-22 | GeminiGuard + OpenAIGuard wrappers in Python SDK | Done | 5 tests |
| T-25 | Graceful Fallback Engine — circuit breaker + offline mode | Done | 9 tests |
| T-26 | Batch scoring + custom weights + self-hosting docs | Done | 8 tests |
| T-27 | Shapley value explainability for Ω_MEM scoring | Done | 8 tests |
| T-28 | Lyapunov stability guarantee for heal loop | Done | 7 tests |
| T-29 | Value of Information (VoI) scoring in importance detector | Done | 6 tests |
| T-30 | ε-Differential Privacy with Laplace mechanism | Done | 10 tests |
| T-31 | Custom thresholds + audit logging + request_id | Done | 6 tests |
| T-32 | GDPR/DPA, SLA tiers, and compliance docs endpoints | Done | 5 tests |
| T-33 | Prometheus metrics export + OpenTelemetry tracing | Done | 6 tests |
| T-34 | Webhook notifications (BLOCK/WARN) — Slack + PagerDuty | Done | 8 tests |
| T-35 | PageRank authority scoring — opt-in 13th component | Done | 7 tests |
| T-36 | Jensen-Shannon divergence ensemble drift detection | Done | 7 tests |
| T-37 | CUSUM + EWMA drift trend detection | Done | 9 tests |
| ML-03–06 | Calibration: Brier, log loss, softmax temperature, logistic meta-layer | Done | 10 tests |
| T-38 | Hawkes self-exciting process for temporal burst detection | Done | 8 tests |
| T-39 | Gaussian copula dependence modeling for joint risk | Done | 7 tests |
| T-40 | Multivariate EWMA (MEWMA) joint trend monitoring | Done | 8 tests |
| SH-01 | Sheaf Cohomology consistency checker — auto source_conflict | Done | 9 tests |
| RL-01 | Causal Q-learning for outcome learning loop | Done | 11 tests |
| BP-01 | Bayesian Online Change Point Detection (BOCPD) | Done | 8 tests |
| RMT-01 | Random Matrix Theory signal/noise separation | Done | 9 tests |
| CG-01 | LiNGAM causal structure discovery | Done | 8 tests |
| IG-01 | α-Divergence as 4th drift detection method | Done | 8 tests |
| SP-01 | Spectral Graph Laplacian for interference analysis | Done | 9 tests |
| MC-01 | Memory Consolidation Score (Hopfield + MI) | Done | 8 tests |
| DS-04 | Jump-Diffusion process for flash-crash detection | Done | 10 tests |
| DS-05 | Regime-Switching HMM for state classification | Done | 10 tests |
| SH-02 | ZK Sheaf proof (FV-06 ZK + SH-01 Sheaf Cohomology) | Done | 9 tests |
| DS-06 | Ornstein-Uhlenbeck mean-reversion recovery prediction | Done | 10 tests |
| FE-01 | Free Energy Functional (variational ELBO) | Done | 9 tests |
| DS-07 | Lévy Flight tail analysis for extreme events | Done | 8 tests |
| OT-01 | Sinkhorn Optimal Transport (accelerated Wasserstein) | Done | 9 tests |
| RD-01 | Rate-Distortion optimal memory retention | Done | 8 tests |

### Also Delivered (Pre-Sprint)

| Item | Description | Status |
|------|-------------|--------|
| Scoring engine | 10-component Ω_MEM formula with Weibull decay | Done |
| R_belief | Model belief divergence (weight 0.05) | Done |
| S_relevance | Intent-drift detection via cosine similarity (weight 0.06) | Done |
| API | 6 endpoints: signup, preflight, heal, outcome, verify, health | Done |
| Auth | Bearer token + Supabase SHA-256 hash lookup | Done |
| Rate limiting | Tier-based monthly limits (free/starter/growth) | Done |
| Stripe billing | Meters + setup script + graduated pricing | Done |
| Landing page | sgraal.com — hero, quickstart, API demo, pricing, signup | Done |
| MCP package | @sgraal/mcp — Claude Desktop + LangGraph middleware | Done |
| Python SDK | pip install sgraal — SgraalClient + @guard decorator | Done |
| MemCube spec | JSON Schema + documentation | Done |
| SEO | llms.txt, sitemap, robots.txt, OpenGraph, JSON-LD | Done |

### Test Summary

- **427 tests passing** (pytest)
- Scoring engine: 31 tests (components, Weibull, belief, relevance, decay ordering)
- API integration: 15 tests (auth, validation, rate limiting, GSV, heal, outcome)
- Self-healing: 8 tests (repair plan, priority, counter)
- Determinism (A2): 5 tests (100-run stress test)
- Importance detector: 9 tests (Budapest use case, signals, at-risk)
- Compliance engine: 7 tests (EU AI Act, FDA, GENERAL, API override)
- Policy matrix: 4 tests (tier/approval lookups)
- Client optimizer: 4 tests (activation, ordering, fresh entries)
- Z3 verification: 9 tests (healing policy, compliance, API endpoint)
- Outcome registry: 6 tests (close, attribution, 404, 409)
- GSV: 7 tests (fallback, stale detection, monotonic)
- Kalman forecast: 8 tests (trends, collapse risk, clamping, API endpoint)
- Dependency graph: 8 tests (surgical block, partial execution, API endpoint)
- Memory tracker: 9 tests (auto-tracking, dependency graph, API auto_tracked, SDK StepTracker)
- Privacy layer: 13 tests (obfuscation, abstraction, ZK commitment, API detail_level)
- Thread manager: 7 tests (sampling rates, bucketing, determinism, API integration)
- LLM guards: 5 tests (GeminiGuard block/warn/pass, OpenAIGuard block/pass)
- Fallback engine: 9 tests (circuit breaker, policies, local scorer, SDK fallback)
- Batch scoring: 5 tests (all results, summary, max 100, empty, auth)
- Custom weights: 3 tests (override, batch, bad sum)
- Shapley values: 8 tests (sum to omega, all components, dominance, negative recovery, API, batch, custom weights, empty)
- Lyapunov stability: 7 tests (V positive, V̇ negative, guaranteed, convergence, decay rates, equilibrium, API)
- Value of Information: 6 tests (positive for stale, zero for fresh, sorted descending, impact correlation, empty, API)
- Differential privacy: 10 tests (noise, determinism, seeds, epsilon scaling, sensitivity, guarantee, API, clamping)
- Custom thresholds: 4 tests (strict, relaxed, API, default)
- Audit log: 2 tests (request_id present, unique per call)
- Compliance endpoints: 5 tests (GDPR fields, SLA tiers, docs profiles, sub-processors, credit policy)
- Metrics/tracing: 6 tests (Prometheus format, JSON format, preflight increment, heal increment, trace attributes, decision distribution)
- Webhooks: 8 tests (register generic/slack/pagerduty, list, delete, 404, auth, HMAC signature)
- PageRank authority: 7 tests (basic PR, score range, empty, opt-in component, opt-out, API with flag, API without)
- Drift detector: 7 tests (identical zero, different positive, JSD bounded, ensemble range, method, empty, API)
- Trend detection: 9 tests (CUSUM upward/stable, EWMA drift/stable, sustained, count, API with/without history)
- Calibration: 10 tests (Brier perfect/overconfident, log loss correct/wrong, softmax sum/keys, meta range/safe, API, empty)
- Hawkes process: 8 tests (baseline, excitation, burst, decay, from_entries, old entries, API, burst via API)
- Copula: 7 tests (low/high joint risk, tail dependence, one low, rho, range, API)
- MEWMA: 8 tests (in control, out of control, T² non-negative, components, custom, history, limit, API)
- Sheaf cohomology: 9 tests (zero, single, consistent, inconsistent, cycles, Jaccard fallback, backward compat, performance, API)
- RL policy: 11 tests (cold start, rewards, Q-update, domain separation, episodes, override, discretization, API, outcome trigger)
- BOCPD: 8 tests (stable, abrupt shift, merkle reset, run length, cold start, hazard sensitivity, API, no history)
- RMT: 9 tests (single/empty null, identical, diverse, signal ratio, Jaccard fallback, performance, API 2+ entries, single entry no rmt)
- Causal graph: 8 tests (single null, insufficient history, two-entry chain, multi-entry DAG, root cause, explanation, LiNGAM with history, API)
- α-Divergence: 8 tests (Hellinger α=0.5, KL limit, α=2.0, numerical stability, ensemble_4, score range, API, backward compat)
- Spectral: 9 tests (single/empty null, two entries, fragmented, dense, Cheeger bound, mixing time, API 2+ entries, single entry no spectral)
- Consolidation: 8 tests (single entry, two entries, fragile detection, stable detection, replay ordering, empty, Hopfield energy, API)
- Jump-Diffusion: 10 tests (insufficient history, no jumps, single jump, flash crash risk, cascade_risk top-level, expected_next_jump, no jump high expected, API response, graceful degradation, cascade requires both)
- HMM Regime: 10 tests (insufficient history, stable state, degrading, critical, Viterbi decoding, regime_collapse_risk top-level, API with history, graceful degradation, regime duration, transition probs)
- ZK Sheaf proof: 9 tests (null when sheaf unavailable, proof valid, proof invalid h1_rank>0, commitment uniqueness, EU AI Act compliance, n_edges count, timestamp format, graceful degradation, API response)
- Ornstein-Uhlenbeck: 15 tests (insufficient history, mean-reverting, non-reverting trend, convergence to μ, half-life, theta non-negative, current deviation, API response, graceful degradation, identical scores, repair_plan wait, repair_plan heal, null no history, equilibrium field, Redis fallback)
- Free Energy: 9 tests (basic computation, ELBO relation, KL non-negative, surprise normalization, first-run init, max tracking, API response, graceful degradation, importance integration)
- Lévy Flight: 8 tests (insufficient history, light tail, heavy tail, cascade_risk integration, repair_plan message, extreme probability bounds, API response, graceful degradation)
- Sinkhorn OT: 9 tests (small payload exact, large payload Sinkhorn, convergence, fallback, iterations count, performance bound, cost normalization, backward compat drift_details, identical distributions)
- Rate-Distortion: 8 tests (single entry, two entries, recommend_delete trigger, keep_score bounds, dynamic lambda, repair_plan integration, compression ratio, graceful degradation)

### Deployments

- **sgraal.com** — Vercel (landing page)
- **app.sgraal.com** — Vercel (dashboard, pending custom domain)
- **api.sgraal.com** — Railway (API)
- **PyPI** — sgraal 0.1.0
- **npm** — @sgraal/mcp 0.1.0

### Commits

153 total (141 in this sprint session)

### Next Up

| Task | Description | Status |
|------|-------------|--------|
| T-22 | PyMC Bayesian calibration (after 50+ outcomes) | Blocked on data |
| T-23 | Webhook notifications for BLOCK/at-risk events | Planned |
| T-24 | SDK v0.2 — add heal() and outcome() methods | Planned |
| T-25 | Multi-agent shared memory governance | Planned |
| T-26 | Full ZK proof implementation (Phase 2) | Planned |
