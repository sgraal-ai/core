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

- **204 tests passing** (pytest)
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

### Deployments

- **sgraal.com** — Vercel (landing page)
- **app.sgraal.com** — Vercel (dashboard, pending custom domain)
- **api.sgraal.com** — Railway (API)
- **PyPI** — sgraal 0.1.0
- **npm** — @sgraal/mcp 0.1.0

### Commits

109 total (97 in this sprint session)

### Next Up

| Task | Description | Status |
|------|-------------|--------|
| T-22 | PyMC Bayesian calibration (after 50+ outcomes) | Blocked on data |
| T-23 | Webhook notifications for BLOCK/at-risk events | Planned |
| T-24 | SDK v0.2 — add heal() and outcome() methods | Planned |
| T-25 | Multi-agent shared memory governance | Planned |
| T-26 | Full ZK proof implementation (Phase 2) | Planned |
