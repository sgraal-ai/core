# Self-Hosting Sgraal

## Quick Start
```bash
cp .env.example .env
# Edit .env with your credentials
# WARNING: Never commit .env to git
docker-compose up -d
```

## Requirements
- Docker 24+
- Supabase project (free tier works)
- Optional: Upstash Redis, Stripe

## Security
- **Never commit .env to git** — it contains API keys and secrets
- Use docker secrets or vault in production
- Enable Supabase RLS on all tables
