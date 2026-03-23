# Self-Hosting Sgraal

Run the full Sgraal stack locally or on your own infrastructure.

## Quick Start

```bash
docker compose up -d
```

This starts:
- **Sgraal API** on `http://localhost:8000`
- **Supabase** (PostgreSQL + PostgREST) on `http://localhost:54321`
- **Redis** (Upstash-compatible) on `http://localhost:6379`

## Environment Variables

Create a `.env` file in the repo root:

```bash
# Supabase (local)
SUPABASE_URL=http://localhost:54321
SUPABASE_KEY=your-local-anon-key
SUPABASE_SERVICE_KEY=your-local-service-key

# Redis (local)
UPSTASH_REDIS_URL=http://localhost:8079
UPSTASH_REDIS_TOKEN=local-token

# Stripe (optional — disable for local dev)
# STRIPE_SECRET_KEY=sk_test_...

# API
PORT=8000
```

## Manual Setup (without Docker)

### 1. API Server

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

### 2. Supabase Local

```bash
# Install Supabase CLI
npm install -g supabase

# Start local Supabase
supabase init
supabase start

# Run migrations
supabase db push < scripts/create_api_keys_table.sql
supabase db push < scripts/create_outcome_log_table.sql
supabase db push < scripts/reset_monthly_calls.sql
```

### 3. Redis Local

```bash
# Option A: Docker
docker run -d -p 6379:6379 redis:alpine

# Option B: Homebrew (macOS)
brew install redis && brew services start redis
```

## Database Migrations

Run these SQL files in the Supabase SQL Editor or via CLI:

1. `scripts/create_api_keys_table.sql` — API key storage with RLS
2. `scripts/create_outcome_log_table.sql` — Outcome tracking
3. `scripts/reset_monthly_calls.sql` — Monthly counter reset (pg_cron)

## Testing

```bash
pip install pytest httpx
python3 -m pytest tests/ -v
```

## Production Deployment

For production self-hosting:

- Use a managed PostgreSQL (Supabase, RDS, Cloud SQL)
- Use Upstash Redis or managed Redis for GSV
- Set `STRIPE_SECRET_KEY` for billing
- Run behind a reverse proxy (nginx, Caddy) with TLS
- Set rate limits at the proxy level in addition to API-level limits
