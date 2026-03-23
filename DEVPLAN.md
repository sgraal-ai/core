# Sgraal Development Plan

## Sprint — 2026-03-23

### Completed Tasks

| Task | Description | Status | Tests |
|------|-------------|--------|-------|
| T-08 | Healing counter + idempotent policy + A2 axiom | Done | 8 tests |
| T-09 | Global State Vector (GSV) via Upstash Redis | Done | 7 tests |
| T-10 | OPA compliance engine — EU AI Act, FDA 510K, HIPAA | Done | 11 tests |
| T-11 | Decision Readiness Dashboard (app.sgraal.com) | Done | mock data |
| T-13 | 4-signal importance detector + at-risk warnings | Done | 9 tests |
| T-14 | Outcome Registry + shadow calibration stub | Done | 6 tests |
| T-15 | GrokGuard — Grok/xAI optimization layer | Done | 4 tests |
| T-17 | Z3 SMT formal verification layer | Done | 9 tests |

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

- **100 tests passing** (pytest)
- Scoring engine: 31 tests (components, Weibull, belief, relevance, decay ordering)
- API integration: 15 tests (auth, validation, rate limiting, GSV, heal, outcome)
- Self-healing: 8 tests (repair plan, priority, counter)
- Determinism (A2): 5 tests (100-run stress test)
- Importance detector: 9 tests (Budapest use case, signals, at-risk)
- Compliance engine: 7 tests (EU AI Act, FDA, GENERAL, API override)
- Policy matrix: 4 tests (tier/approval lookups)
- GrokGuard: 4 tests (activation, ordering, fresh entries)
- Z3 verification: 9 tests (healing policy, compliance, API endpoint)
- Outcome registry: 6 tests (close, attribution, 404, 409)
- GSV: 7 tests (fallback, stale detection, monotonic)

### Deployments

- **sgraal.com** — Vercel (landing page)
- **app.sgraal.com** — Vercel (dashboard, pending custom domain)
- **api.sgraal.com** — Railway (API)
- **PyPI** — sgraal 0.1.0
- **npm** — @sgraal/mcp 0.1.0

### Commits

66 total (54 in this sprint session)

### Next Up

| Task | Description | Status |
|------|-------------|--------|
| T-12 | Live API connection for dashboard (replace mock data) | Planned |
| T-16 | Multi-agent shared memory governance | Planned |
| T-18 | PyMC Bayesian calibration (after 50+ outcomes) | Blocked on data |
| T-19 | Webhook notifications for BLOCK/at-risk events | Planned |
| T-20 | SDK v0.2 — add heal() and outcome() methods | Planned |
