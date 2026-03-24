# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sgraal is a memory governance protocol for AI agents. It provides a preflight scoring engine that evaluates whether an AI agent's memory state is reliable enough to act on, returning a risk score (Ω_MEM) and a recommended action (USE_MEMORY, WARN, ASK_USER, BLOCK).

## Architecture

- **`scoring_engine/`** — Core Ω_MEM computation engine (pure Python, no dependencies). `omega_mem.py` contains the weighted scoring formula using 10 risk components (freshness, drift, provenance, propagation, recall, encode, interference, recovery, r_belief, s_relevance), scaled by action-type and domain criticality multipliers. S_freshness uses Weibull decay per memory type: tool_state (0.15, fast) > shared_workflow > episodic > preference > semantic > policy > identity (0.002, near-permanent). R_belief (weight 0.05) measures model belief divergence. S_relevance (weight 0.06) detects intent-drift via cosine similarity. Tier 1 self-healing generates a `repair_plan` with actions: REFETCH (freshness>60), VERIFY_WITH_SOURCE (conflict>50), REBUILD_WORKING_SET (belief<0.3), each with projected_improvement and priority. `healing_counter` tracks cumulative heals across entries. Healing policies defined in `healing_policy.yaml` (rule_id, condition, action, tier, idempotent). A2 axiom enforced: identical memory state + identical healing_counter = identical Ω_MEM score (deterministic, no randomness). `importance_detector.py` provides 4-signal importance detection: return_frequency, blast_radius, irreversibility, uniqueness → importance_score (0–10). At-risk when score >= 5.0 AND age > 70% of type threshold (tool_state=7d, semantic=100d, policy=200d, identity=500d). Preflight response includes `at_risk_warnings` with data-driven natural language warnings. `client_optimizer.py` provides generic client optimization — activated via `client` field in preflight request (any profile: grok, langchain, autogen, crewai, etc.), prioritizes REFETCH for stale tool_state entries, re-orders repair plan. Response includes `client_optimized` and `optimizer_version` (v2). `compliance_engine.py` evaluates against regulatory profiles (GENERAL, EU_AI_ACT, FDA_510K, HIPAA) — EU AI Act enforces Article 12 (blocks irreversible+high risk), Article 9 (medical oversight), Article 13 (transparency). Critical violations override recommended_action to BLOCK. `healing_policy_matrix.py` maps memory_type × domain × profile to healing tier and approval requirements. Preflight accepts optional `compliance_profile`, response includes `compliance_result`. `formal_verification.py` provides Z3 SMT verification of healing policies (no contradictions, BLOCK reachable, counter monotonic) and compliance rules (no rule both allows and blocks same action). Graceful fallback to logical verification when Z3 unavailable. `GET /v1/verify` endpoint runs both checks and accepts optional `history` parameter (comma-separated scores) for Kalman filter trend forecasting. `kalman_forecast.py` provides `KalmanForecaster` (1D Kalman, process_noise=0.1, measurement_noise=1.0) → trend (improving/stable/degrading), collapse_risk (0–1, probability of hitting BLOCK), and forecast_scores. `dependency_graph.py` enables surgical BLOCK — tracks step → entry dependencies, only halts steps that depend on stale entries while safe steps proceed. Preflight accepts optional `steps` field, returns `surgical_result` (blocked_steps, safe_steps, partial_execution_possible). `memory_tracker.py` auto-detects step→entry dependencies without manual declaration — when no `steps` provided, each entry becomes its own step (`auto:{id}`), response includes `auto_tracked: true`. Python SDK `StepTracker` context manager tracks access within step blocks. `privacy_layer.py` provides 3-layer protection: Layer 1 HMAC-SHA256 entry ID obfuscation per session, Layer 2 reason abstraction to categories (STALE/CONFLICT/LOW_TRUST/PROPAGATION_RISK/INTENT_DRIFT), Layer 3 ZK commitment hash. Default `detail_level="obfuscated"`, opt-in `detail_level="full"` for original IDs. Response includes `session_key` and `zk_commitment`. `thread_manager.py` provides thread bucketing + adaptive sampling for million-scale deployments — consistent hashing assigns threads to buckets, domain-based sample rates (medical/fintech/legal=100%, coding/customer_support=10%, general=50%). Sampled-out threads get lightweight USE_MEMORY response. Preflight accepts optional `thread_id`, response includes `sampled`, `bucket_id`, `sample_rate`. `shapley_explain.py` computes per-component Shapley values showing each component's contribution to the final Ω_MEM score (positive = increases risk, negative = decreases risk). Included in `/v1/preflight` and `/v1/preflight/batch` responses as `shapley_values`. `lyapunov.py` provides formal stability guarantee for the heal loop — V(x) = ω²/200 (positive definite), V̇(x) = -decay × V(x) (negative definite), proving asymptotic convergence. `/v1/heal` response includes `lyapunov_stability` (V, V_dot, converging, guaranteed). `importance_detector.py` also computes Value of Information (VoI) per entry — `voi_score` = expected Ω_MEM improvement if that entry were healed. At-risk warnings sorted by VoI descending (highest ROI first). `differential_privacy.py` implements ε-Differential Privacy via Laplace mechanism — Pr[M(D)∈S] ≤ exp(ε)·Pr[M(D')∈S] guaranteed. Deterministic seeded noise preserves A2 axiom. Preflight accepts optional `dp_epsilon`, response includes `privacy_guarantee` (epsilon, mechanism, dp_satisfied). Custom decision thresholds via `thresholds` field (e.g. `{"warn": 40, "ask_user": 60, "block": 80}`). Audit logging: every preflight/heal call logged to Supabase `audit_log` with request_id, api_key_id, decision, omega_score. `request_id` (uuid) in every preflight response. `pagerank.py` computes PageRank authority scores (d=0.85) over memory dependency graph — opt-in via `use_pagerank: true`, adds `r_importance` as 13th component (weight 0.04, risk = authority × freshness) and `authority_scores` (0–10 per entry) to response. `drift_detector.py` computes Jensen-Shannon divergence alongside KL divergence and Wasserstein distance — ensemble of all three (equal weights) for s_drift detection. Every preflight response includes `drift_details` (kl_divergence, wasserstein, jsd, drift_method: ensemble). `trend_detection.py` provides CUSUM (S⁺ₜ/S⁻ₜ, h=5) and EWMA (λ=0.2, 3σ) detectors — `drift_sustained=true` when 4+ consecutive degradations and both agree. Preflight accepts optional `score_history`, returns `trend_detection` (cusum_alert, ewma_alert, drift_sustained, consecutive_degradations). `calibration.py` provides ML calibration layer: Brier score (assurance accuracy), log loss (penalizes confident errors), softmax temperature scaling (T=1.5, smooths overconfident scores), logistic meta-layer P(unsafe)=σ(β₀+Σβᵢ·Cᵢ). Every preflight response includes `calibration` (brier_score, log_loss, calibrated_scores, meta_score).
- **`api/`** — FastAPI REST API. Endpoints: `/v1/preflight` (scoring), `/v1/preflight/batch` (up to 100 entries, returns per-entry results + batch_summary), `/v1/heal`, `/v1/outcome`, `/v1/signup`, `/v1/verify`, `/v1/compliance/gdpr` (data retention, erasure, portability, DPA), `/v1/compliance/sla` (4 tiers with uptime/latency/credit policy), `/v1/compliance/docs` (EU AI Act, GDPR, FDA 510K, HIPAA profiles), `/health`. Both preflight endpoints accept optional `custom_weights` and `thresholds`. `/metrics` exports Prometheus-format metrics (preflight_total, heal_total, decision distribution, avg omega, p95 response time) and JSON via `?accept=json`. Preflight responses include `_trace` with OpenTelemetry span attributes (api_key_id, decision, omega_score, request_id, duration_ms). `/v1/webhooks` (POST register, GET list, DELETE remove) dispatches HMAC-signed notifications on BLOCK/WARN/ASK_USER decisions to generic, Slack, or PagerDuty targets. Optionally logs to Supabase (`memory_ledger` + `audit_log` tables). Self-hosting: `Dockerfile` + `docker-compose.yml` + `SELF_HOSTING.md`.
- **`examples/`** — Usage examples for the scoring engine.
- **`web/`** — Next.js landing page deployed to Vercel at [sgraal.com](https://www.sgraal.com). Sections: hero, how it works, API demo, pricing, signup form. Includes `/privacy` and `/terms` pages. Uses `NEXT_PUBLIC_API_URL` env var to point at the API.
- **`dashboard/`** — Decision Readiness Dashboard (Next.js, deployed to Vercel). Connected to live Sgraal API — enter API key via Settings panel (gear icon, saved to localStorage). Demo fleet with 5 agents sends real preflight calls. Falls back to mock data with banner when no API key set. Pages: `/` fleet overview with OmegaMeter gauges and agent cards, `/agent/[id]` detail with component breakdown/repair plan/at-risk warnings/compliance violations, `/verify` Z3 verification status per profile. Deploy: `cd dashboard && vercel --prod`.
- **`mcp/`** — `@sgraal/mcp` npm package. MCP server (`sgraal_preflight` tool) for Claude Desktop, plus `createGuard()` and `withPreflight()` middleware for LangGraph/Node.js. Reads `SGRAAL_API_KEY` from env. Blocks on BLOCK, warns on WARN, passes through on USE_MEMORY.
- **`spec/`** — MemCube specification. `memcube.schema.json` defines the standardized memory entry format (JSON Schema draft 2020-12). 7 required fields (id, content, type, timestamp_age_days, source_trust, source_conflict, downstream_count) and 6 optional fields (goal_id, source, provenance, gsv, context_tags, geo_tag). Memory types: episodic, semantic, preference, tool_state, shared_workflow, policy, identity. See `MEMCUBE.md` for field documentation and examples.
- **`sdk/python/`** — `sgraal` PyPI package (`pip install sgraal`). `SgraalClient` with `preflight()` and `signup()`, circuit breaker (3 failures → OPEN, 30s recovery), local Weibull-only fallback scoring when API unavailable. `@guard()` decorator with `block_on` and `fallback_policy` (allow/warn/block). `GeminiGuard` and `OpenAIGuard` wrap google-generativeai and openai SDKs. `StepTracker` context manager. Publish: `cd sdk/python && python -m build && twine upload dist/*`.
- **`scripts/`** — Stripe setup, Supabase migrations, pg_cron monthly reset, outcome_log table migration, and `shadow_calibration.py` (reads closed outcomes from Supabase, counts component attribution frequencies, prints suggested β weight adjustments — stub until 50+ outcomes collected).

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run API server locally
uvicorn api.main:app --reload

# Run tests
pip install pytest httpx
python3 -m pytest tests/ -v

# Run example scoring
python examples/basic_usage.py
```

## Deployment

**API** — Deployed on Railway via `Procfile`:
```
web: PYTHONPATH=/app python3 -m uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

**Landing page** — Deployed on Vercel from `web/`:
```bash
cd web && vercel --prod
```
Env var: `NEXT_PUBLIC_API_URL=https://api.sgraal.com` (set in Vercel project settings).

## Environment Variables

- `SUPABASE_URL` — Supabase project URL (optional, enables logging)
- `SUPABASE_KEY` — Supabase anon key (optional, enables logging)
- `SUPABASE_SERVICE_KEY` — Supabase service role key (required for signup, bypasses RLS for api_keys inserts)
- `STRIPE_SECRET_KEY` — Stripe secret key (optional, enables billing and signup)
- `UPSTASH_REDIS_URL` — Upstash Redis REST URL (optional, enables Global State Vector)
- `UPSTASH_REDIS_TOKEN` — Upstash Redis auth token (optional, enables GSV)

## Database Setup

The `api_keys` table migration is at `scripts/create_api_keys_table.sql`. Schema: `id` (uuid), `created_at`, `key_hash` (unique, indexed), `customer_id` (Stripe, indexed), `email`, `tier` (free/starter/growth), `calls_this_month`, `last_used_at`. RLS enabled: users see only their own keys; only service role can insert/delete.

The `outcome_log` table migration is at `scripts/create_outcome_log_table.sql`. Schema: `outcome_id` (uuid), `preflight_id`, `agent_id`, `task_id`, `status` (open/success/failure/partial), `component_attribution` (jsonb), `created_at`, `closed_at`. Service role full access via RLS.

## Authentication

The `/v1/preflight` endpoint requires a Bearer token in the `Authorization` header. API keys are validated against the in-memory `API_KEYS` dict first, then fall back to a SHA-256 hash lookup in the Supabase `api_keys` table. Returns 401 for invalid keys, 403 if the header is missing.

## API Endpoints

`POST /v1/signup` — accepts `{ "email": "..." }`. Creates a Stripe customer, subscribes to the free tier, generates a secure API key (`sg_live_` prefix), stores the SHA-256 hash in Supabase `api_keys`, and returns the plaintext key once.

`POST /v1/preflight` — requires `Authorization: Bearer <api_key>`. Accepts `memory_state` (list of memory entries with trust/conflict/age metadata), `action_type` (informational/reversible/irreversible/destructive), `domain` (general/customer_support/coding/legal/fintech/medical), and optional `client_gsv` (integer). The Stripe customer ID is resolved automatically from the API key. Returns `omega_mem_final` score, `recommended_action`, `assurance_score`, `component_breakdown`, `repair_plan`, `healing_counter`, `gsv`, and `outcome_id` (uuid for closing via `/v1/outcome`). If `client_gsv` is provided and server GSV < client_gsv, returns `stale_state_warning: STALE_STATE_DETECTED`. GSV increments monotonically via Upstash Redis INCR (falls back to 0 if Redis unavailable).

`POST /v1/heal` — requires `Authorization: Bearer <api_key>`. Accepts `entry_id` (string), `action` (REFETCH/VERIFY_WITH_SOURCE/REBUILD_WORKING_SET), and optional `agent_id`. Increments the per-entry healing counter and returns `healed`, `healing_counter`, `projected_improvement`, `action_taken`, and `timestamp`. Logged to Supabase `memory_ledger`.

`POST /v1/outcome` — requires `Authorization: Bearer <api_key>`. Closes an outcome from a previous preflight call. Accepts `outcome_id`, `status` (success/failure/partial), and `failure_components` (list of β component names for attribution). Returns `outcome_id`, `status`, `closed_at`. Logged to Supabase `outcome_log`. Returns 404 for unknown outcome_id, 409 if already closed.

## Rate Limiting

Monthly call limits enforced per API key via `calls_this_month` in the `api_keys` table: free (10,000), starter (100,000), growth (1,000,000). Returns 429 when exceeded. Counter increments and `last_used_at` updates on every successful preflight call. In-memory test keys skip rate limiting.

## Billing

Usage-based billing via Stripe Meters. Every `/v1/preflight` call emits an `omega_mem_preflight` meter event attributed to the request's `stripe_customer_id`. Free tier: first 10,000 calls per customer are free (configured in Stripe pricing).

One-time Stripe setup (creates meter, product, and graduated pricing):
```bash
STRIPE_SECRET_KEY=sk_test_... python scripts/setup_stripe.py
```

## MCP Package

`@sgraal/mcp` — install with `npm install @sgraal/mcp`, publish with `cd mcp && npm publish --access public`.

Build: `cd mcp && npm run build`. Claude Desktop config:
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
