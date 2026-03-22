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
- `SUPABASE_KEY` — Supabase service key (optional, enables logging)
- `STRIPE_SECRET_KEY` — Stripe secret key (optional, enables usage-based billing via Stripe Meters)

## Key API Endpoint

`POST /v1/preflight` — accepts `stripe_customer_id`, `memory_state` (list of memory entries with trust/conflict/age metadata), `action_type` (informational/reversible/irreversible/destructive), and `domain` (general/customer_support/coding/legal/fintech/medical). Returns `omega_mem_final` score, `recommended_action`, `assurance_score`, and `component_breakdown`.

## Billing

Usage-based billing via Stripe Meters. Every `/v1/preflight` call emits an `omega_mem_preflight` meter event attributed to the request's `stripe_customer_id`. Free tier: first 10,000 calls per customer are free (configured in Stripe pricing).
