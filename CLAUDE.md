# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sgraal is a memory governance protocol for AI agents. It provides a preflight scoring engine that evaluates whether an AI agent's memory state is reliable enough to act on, returning a risk score (Ω_MEM) and a recommended action (USE_MEMORY, WARN, ASK_USER, BLOCK).

## Architecture

- **`scoring_engine/`** — Core Ω_MEM computation engine (pure Python, no dependencies). `omega_mem.py` contains the weighted scoring formula using 8 risk components (freshness, drift, provenance, propagation, recall, encode, interference, recovery), scaled by action-type and domain criticality multipliers.
- **`api/`** — FastAPI REST API exposing `POST /v1/preflight` as the single scoring endpoint. Optionally logs results to Supabase (`memory_ledger` table) when `SUPABASE_URL` and `SUPABASE_KEY` env vars are set.
- **`examples/`** — Usage examples for the scoring engine.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run API server locally
uvicorn api.main:app --reload

# Run example scoring
python examples/basic_usage.py
```

## Deployment

Deployed on Railway via `Procfile`:
```
web: PYTHONPATH=/app python3 -m uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

## Environment Variables

- `SUPABASE_URL` — Supabase project URL (optional, enables logging)
- `SUPABASE_KEY` — Supabase anon key (optional, enables logging)
- `SUPABASE_SERVICE_KEY` — Supabase service role key (required for signup, bypasses RLS for api_keys inserts)
- `STRIPE_SECRET_KEY` — Stripe secret key (optional, enables billing and signup)

## Database Setup

The `api_keys` table migration is at `scripts/create_api_keys_table.sql`. Run it in the Supabase SQL Editor or via CLI. Schema: `id` (uuid), `created_at`, `key_hash` (unique, indexed), `customer_id` (Stripe, indexed), `email`, `tier` (free/starter/growth), `calls_this_month`, `last_used_at`. RLS enabled: users see only their own keys by email; only service role can insert/delete.

## Authentication

The `/v1/preflight` endpoint requires a Bearer token in the `Authorization` header. API keys are validated against the in-memory `API_KEYS` dict first, then fall back to a SHA-256 hash lookup in the Supabase `api_keys` table. Returns 401 for invalid keys, 403 if the header is missing.

## API Endpoints

`POST /v1/signup` — accepts `{ "email": "..." }`. Creates a Stripe customer, subscribes to the free tier, generates a secure API key (`sg_live_` prefix), stores the SHA-256 hash in Supabase `api_keys`, and returns the plaintext key once.

`POST /v1/preflight` — requires `Authorization: Bearer <api_key>`. Accepts `memory_state` (list of memory entries with trust/conflict/age metadata), `action_type` (informational/reversible/irreversible/destructive), and `domain` (general/customer_support/coding/legal/fintech/medical). The Stripe customer ID is resolved automatically from the API key. Returns `omega_mem_final` score, `recommended_action`, `assurance_score`, and `component_breakdown`.

## Rate Limiting

Monthly call limits enforced per API key via `calls_this_month` in the `api_keys` table: free (10,000), starter (100,000), growth (1,000,000). Returns 429 when exceeded. Counter increments and `last_used_at` updates on every successful preflight call. In-memory test keys skip rate limiting.

## Billing

Usage-based billing via Stripe Meters. Every `/v1/preflight` call emits an `omega_mem_preflight` meter event attributed to the request's `stripe_customer_id`. Free tier: first 10,000 calls per customer are free (configured in Stripe pricing).

One-time Stripe setup (creates meter, product, and graduated pricing):
```bash
STRIPE_SECRET_KEY=sk_test_... python scripts/setup_stripe.py
```
