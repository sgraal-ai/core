# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sgraal is a memory governance protocol for AI agents. It provides a preflight scoring engine that evaluates whether an AI agent's memory state is reliable enough to act on, returning a risk score (Ω_MEM) and a recommended action (USE_MEMORY, WARN, ASK_USER, BLOCK).

## Architecture

### Module boundaries — what lives where

```
api/
├── main.py             ~17,300 lines  — preflight orchestration, endpoint handlers, Pydantic models
├── tenant.py                80 lines  — TenantContext for structural tenant isolation
├── detection.py           ~870 lines  — 6 detection layers, naturalness, secret patterns, attack surface
├── helpers.py              354 lines  — dict management, SSRF validation, anomaly detection, rate limiting
├── webhooks.py             ~170 lines — webhook dispatch, DNS-pinned dispatch, Slack/PagerDuty formatters
├── vaccination.py          143 lines  — AES-256-GCM vaccine encryption/decryption (XOR fallback removed)
├── fleet.py                ~160 lines — Redis circuit breaker (thread-safe), PagerDuty/OpsGenie alerting
├── redis_state.py                    — Redis REST client (Upstash), thread-safe session, large payload POST
└── routers/
    ├── guard.py                      — /v1/guard/* function-calling endpoints
    ├── vaccines.py          62 lines — /v1/vaccines/*, /v1/compromised-agents/*
    ├── sla_feeds.py        188 lines — /v1/sla/*, /v1/feed/*, /v1/sla-rules/*
    ├── registry.py          66 lines — /v1/registry/*
    └── federation.py        53 lines — /v1/federation/*

scoring_engine/                       — Pure Python scoring (no dependencies on api/)
├── omega_mem.py                      — 10-component weighted scoring formula + Weibull decay
├── constants.py                      — DecisionAction enum, thresholds, Landauer constants
├── 80+ module files                  — Analytics modules (drift, calibration, HMM, etc.)
```

### Core scoring

`scoring_engine/omega_mem.py` — 10 risk components (s_freshness, s_drift, s_provenance, s_propagation, r_recall, r_encode, s_interference, s_recovery, r_belief, s_relevance), scaled by action-type and domain multipliers. s_recovery has **negative weight** (-0.10) — recovery capability reduces risk. Weights sum to 0.95 (0.99 with PageRank). Normalized by sum(abs(weights)) so omega is always [0, 100].

S_freshness uses Weibull decay per memory type: tool_state (λ=0.15, fast) > shared_workflow > episodic > preference > semantic > policy > identity (λ=0.002, near-permanent).

A2 axiom: identical memory state + identical healing_counter = identical Ω_MEM score (deterministic, no randomness).

### API layer

`api/main.py` — 366+ endpoints. Key endpoints:
- `/v1/preflight` — full 83-module scoring pipeline
- `/v1/check` — simple door (plain strings in, plain English out, no MemCube required)
- `/v1/heal` — increment healing counter, Lyapunov stability proof
- `/v1/outcome` — close outcome for Q-learning
- `/v1/signup` — Stripe + Supabase API key generation
- `/v1/verify` — Z3 SMT + healing policy verification

`_preflight_internal()` (~5,098 lines) is the core orchestration function containing inline enrichment, detection overrides, and response construction. Not yet refactored into smaller units.

### Detection layers (api/detection.py)

6 post-reconciliation layers that cannot be overridden:
1. `_check_timestamp_integrity` (Round 6) — content-age mismatch, fleet age collapse
2. `_check_identity_drift` (Round 7) — authority expansion, subject rebinding
3. `_check_consensus_collapse` (Round 8) — collapse ratio, federation asymmetry
4. `_check_provenance_chain` (Round 9+) — circular refs, compromised agents, PA signals
5. `_check_sync_bleed` (Round 12) — stale/fresh version mixing, cross-version Jaccard
6. `_check_confidence_calibration` (Round 12) — correlated consensus, stale-but-confident, model confidence divergence

All MANIPULATED → BLOCK. Corroboration gates prevent single-signal escalation. `_compute_attack_surface_score` composites all 6 layers. Plugin `on_preflight_complete` hook enforces security monotonicity (cannot downgrade decisions).

### Invariant validation (api/invariants.py)

Explicit 4-invariant check before the 83-module pipeline:
- I1 Identity Invariance — duplicate IDs with different content → fast-path BLOCK
- I2 Time Validity — negative ages → fast-path BLOCK; past-year markers → ambiguous
- I3 Evidence Independence — >80% identical trust/conflict → ambiguous
- I4 Provenance Integrity — circular chains → fast-path BLOCK

Clear violations skip the scoring engine entirely. Response includes `invariant_check` field.

### Fleet health phase (POST /v1/fleet/health-phase)

SIR epidemiology analog: computes fresh-entry ratio vs domain-specific critical threshold p_c. Returns `sub_critical` / `critical` / `super_critical` phase. Domain thresholds: general=0.08, coding=0.12, fintech=0.28, medical=0.22.

### Decision stability (stability_delta in preflight response)

Lyapunov analog: `stability_delta` (float [-1, +1]) and `stability_trend` (stabilizing/stable/destabilizing). Informational only — does not affect `recommended_action`. Computed from omega change since last preflight for the same (tenant, agent_id).

### MVCC Redis state versioning (api/redis_state.py)

Compare-And-Swap pattern for concurrent Redis updates: `redis_mvcc_get(key)` → (value, version), `redis_mvcc_update(key, updater_fn, ttl, max_retries)` → MVCCResult. Uses Lua script for atomicity. Versioned values stored as `{_v: N, _d: data}`. Legacy unversioned values treated as version 0. Opt-in — existing writes don't require MVCC.

### SSE streaming (POST /v1/preflight/stream)

23 intermediate events across 4 phases: 15 scoring module_complete → 6 detection_complete (layer states) → 1 invariant_check → 1 complete (final decision). Progress percentage monotonically increases. Events emitted post-computation (pipeline runs first, results replayed as stream).

### Other key subsystems

- **Plugin system** — registry-only, per-tenant isolation, no remote code upload
- **Edge mode** — `sgraal.edge` zero-dependency SDK for offline/embedded scoring
- **W3C VCs** — `POST /v1/certify` issues SgraalProof2026 credentials
- **Memory Vaccination** — attack signatures encrypted at rest (AES-256-GCM), fleet-wide immunity, deferred vaccination after detection overrides
- **RL Q-learning** — per-domain Q-tables, updated via `/v1/outcome`
- **Bridge SDKs** (27 integrations) — cloudflare-sgraal, mem0-sgraal, sgraal-llamaindex, etc.
- **MCP server** — `@sgraal/mcp` npm package for Claude Desktop
- **Dashboard** — Next.js at app.sgraal.com, connected to live API
- **Landing page** — Static HTML at sgraal.com (web-static/)

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run API server locally
uvicorn api.main:app --reload

# Run tests (2,545+ tests across 33+ test files)
pip install pytest httpx
python3 -m pytest tests/ -v

# Run single test file
python3 -m pytest tests/test_api_key_cache.py -v

# Run benchmark corpora against live API
python3 tests/corpus/run_all.py

# Build dashboard
cd dashboard && npx next build

# Deploy dashboard
cd dashboard && vercel --prod

# Deploy landing page
cd web-static && vercel --prod
```

## Testing

### Baseline — do not drop below:
- pytest: 2,643 passing (as of 2026-04-23)
- Corpus: 1,190+ adversarial cases (Rounds 1-11)
- Round 12: 43/60 exact match, 24/24 hard BLOCK, 20% control FP rate
- R2 F1: 1.0000 (must not regress)

### Session audit summary (2026-04-22/23):
- **3 audits**: 111+, 46, and 56 findings (213 total)
- **70 commits**: 46 (audit #1) + 46 (audit #2) + 15 (audit #3) + 4 (R12 thresholds) + 1 (docs) + 7 (TenantContext) + 1 (CI check)
- **0 regressions**: all baselines preserved throughout

### Scoring weight note:
- `s_recovery` has **negative weight** (-0.10) — intentional
- Weights normalized by `sum(abs(applied_weights))` so omega ∈ [0, 100]
- `s_relevance` uses TF-IDF fallback (Jaccard) when no embeddings provided

### When to run tests:
- **pytest**: only when `api/` or `tests/` files change
- **corpus**: only when scoring logic changes
- **NEVER run for**: frontend, docs, SDK, README changes

### Before pushing api/main.py:
```bash
python3 -c "import ast; ast.parse(open('api/main.py').read())"
```

### Test files (35+ files):
- `test_scoring.py` — Core scoring engine (1840+ tests)
- `test_security_audit.py` — Cross-tenant isolation, SSRF, secrets (27 tests)
- `test_tenant_context.py` — TenantContext unit tests (25 tests)
- `test_tenant_isolation.py` — Cross-tenant integration tests
- `test_timestamp_integrity.py` — Round 6 detection (17 tests)
- `test_identity_drift.py` — Round 7 detection (19 tests)
- `test_consensus_collapse.py` — Round 8 detection (17 tests)
- `test_attack_surface_score.py` — Compound attack surface (13 tests)
- `test_check_endpoint.py` — /v1/check simple door (8 tests)
- `test_public_rate_limit.py` — IP-based rate limiting (4 tests)
- `test_vaccination.py` + `test_vaccine_encryption.py` — Vaccination system (10 tests)
- `test_infra_features.py` — Circuit breaker, guard endpoints (15 tests)
- See `tests/` directory for full list

## Deployment

**API** (api.sgraal.com) — Railway, auto-deploys from main:
```
web: PYTHONPATH=/app python3 -m uvicorn api.main:app --host 0.0.0.0 --port $PORT --workers 4
```

**Dashboard** (app.sgraal.com) — Vercel: `cd dashboard && vercel --prod`

**Landing page** (sgraal.com) — Vercel: `cd web-static && vercel --prod`

**Staging** — Railway staging env, config in `railway.staging.toml`. Staging-first workflow: branch → local uvicorn test → merge to main.

## Environment Variables

- `SUPABASE_URL` / `SUPABASE_KEY` — optional, enables logging
- `SUPABASE_SERVICE_KEY` — required for signup (bypasses RLS)
- `STRIPE_SECRET_KEY` — optional, enables billing
- `UPSTASH_REDIS_URL` / `UPSTASH_REDIS_TOKEN` — optional, enables GSV + caching
- `ATTESTATION_SECRET` — **required in production** (HMAC proof hashes)
- `PASSPORT_SIGNING_KEY_V1` — **required in production** (Memory Passports)
- `UNSUB_HMAC_SECRET` — **required in production** (email unsubscribe tokens)
- `SGRAAL_SKIP_DNS_CHECK=1` — skip DNS in tests (webhook SSRF validation)
- `SGRAAL_TEST_MODE=1` — enable test API keys (NEVER in production)

## Security Architecture

### Tenant isolation
All per-tenant data keyed by `_safe_key_hash(key_record)` — never returns "default" or empty string. Test keys get deterministic SHA-256 from the API key.

**TenantContext pattern** (`api/tenant.py`) — structural enforcement of per-tenant data access. Every endpoint that touches tenant-scoped data should declare:
```python
from api.tenant import TenantContext
tenant: TenantContext = Depends(get_tenant_context)
```
TenantContext provides: `.key_hash`, `.filter_list(items)`, `.owns(item)`, `.assert_owns(item)`, `.tag(item)`, `.scoped_key(*parts)`, `.redis_key(prefix, *parts)`, `.supabase_filter(url)`.

**CI enforcement**: `scripts/check_tenant_isolation.py` — AST-based check that fails the build if any endpoint accesses a tenant-scoped collection without TenantContext or `_safe_key_hash`. Run: `python3 scripts/check_tenant_isolation.py --strict`.

### Rate limiting
Quota: atomic Redis INCR on `quota:{key_hash}:{year_month}` (35-day TTL). Tiers: free (10K), starter (100K), growth (1M).
Public endpoints: IP-based 60 req/min via `_check_public_rate_limit()`.

### SSRF protection
`_validate_webhook_url()` blocks http://, private IPs, loopback, link-local, cloud metadata, .local/.internal hostnames. DNS cache prevents rebinding.

### Redis TTL policy
All `redis_set` calls must include explicit TTL. No indefinite keys.

## Authentication

Bearer token in `Authorization` header. Validation order: (1) in-memory API_KEYS, (2) Redis cache (TTL 300s), (3) Supabase SHA-256 hash lookup. Demo key `sg_demo_playground` works on non-sensitive endpoints.

## API Endpoints

366+ endpoints. Key groups:
- Preflight: `/v1/preflight`, `/v1/check`, `/v1/preflight/batch`
- Healing: `/v1/heal`, `/v1/outcome`
- Compliance: `/v1/compliance/eu-ai-act/report`, `/v1/compliance/gdpr`, `/v1/compliance/nist-ai-rmf`
- Verification: `/v1/verify`, `/v1/certify`, `/v1/verify-attestation`
- Fleet: `/v1/vaccines`, `/v1/compromised-agents`, `/v1/federation/*`
- Admin: `/health`, `/v1/scheduler/status`, `/v1/analytics/*`

Valid domains: general, customer_support, coding, legal, fintech, medical.
Valid action_types: informational, reversible, irreversible, destructive.

## MCP Package

`@sgraal/mcp` — `npm install @sgraal/mcp`. Claude Desktop config:
```json
{
  "mcpServers": {
    "sgraal": {
      "command": "npx",
      "args": ["@sgraal/mcp"],
      "env": { "SGRAAL_API_KEY": "sg_live_..." }
    }
  }
}
```
