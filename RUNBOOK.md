# RUNBOOK.md — Emergency Operations

## Rollback a bad deploy

Railway auto-deploys from main. To roll back:

```bash
# Find the last good commit
git log --oneline -10

# Revert the bad commit
git revert {bad_commit_hash} --no-edit
git push
```

Railway will auto-deploy the revert. Typically takes 2-3 minutes.

## Check Railway deploy status

```bash
railway status
# Or check the Railway dashboard: https://railway.app/dashboard
```

## Restart the service

```bash
railway up --detach
# Or use the Railway dashboard: Settings → Restart
```

## Check logs

```bash
railway logs --tail 100
# Or use the Railway dashboard: Deployments → Latest → Logs
```

## Health check

```bash
curl https://api.sgraal.com/health | python3 -m json.tool
```

If status is "unhealthy" → Redis is down. Check Upstash dashboard.
If status is "degraded" → Supabase is down or slow. Check Supabase dashboard.

## Emergency: secrets rotated accidentally

See KEYS.md for the full key rotation procedure. Summary:
1. ATTESTATION_SECRET rotated → all W3C VCs invalid
2. PASSPORT_SIGNING_KEY_V1 rotated → all passports invalid
3. UNSUB_HMAC_SECRET rotated → all unsubscribe links broken

There is NO automatic migration. Re-issue affected artifacts manually.

## Security incident: API key leaked

1. Identify the leaked key (check audit_log for suspicious activity)
2. Revoke the key: DELETE from Supabase api_keys table
3. Invalidate Redis cache: DEL api_key_valid:{hash[:16]}
4. Notify the customer to generate a new key
5. Check /v1/security/key-activity for the leaked key's anomaly signals

## Container security

The Dockerfile runs as non-root user. The Helm chart enforces:
- runAsNonRoot: true
- readOnlyRootFilesystem: false (needed for tmp files)
- drop ALL capabilities

## Staging vs Production

### Staging URL
- `api-staging.sgraal.com` (requires DNS CNAME pointing to the Railway staging service after environment is created)

### Purpose
Every push to `main` deploys to staging first. Verify staging is healthy before promoting to production. Staging uses `railway.staging.toml` for environment-specific config (`ENVIRONMENT=staging`, `LOG_LEVEL=debug`).

### Deploy to staging
Staging auto-deploys from `main` when the Railway staging environment is configured:
```bash
git push origin main  # staging auto-deploys from main
```

Manual deploy (first-time setup or re-deploy):
```bash
railway environment staging
railway up
```

### Verify staging health
```bash
curl https://api-staging.sgraal.com/health | python3 -m json.tool
```
Logs will show `STAGING MODE — not production` on startup.

### Promote staging to production
After verifying staging is healthy, promote via the Railway dashboard:
1. Open Railway dashboard → select project
2. Switch to production environment
3. Click "Deploy" → select the same commit that staging is running
4. Verify: `curl https://api.sgraal.com/health`

### Deploy to production (direct)
Production auto-deploys from `main` branch. Manual deploy:
```bash
railway environment production
railway up
```

### Environment variables for staging
Staging should use separate credentials where possible:
- `ENVIRONMENT=staging` (set via `railway.staging.toml`; CORS restricts localhost; startup log shows staging mode)
- `LOG_LEVEL=debug` (verbose logging for troubleshooting)
- Separate `SUPABASE_URL` / `SUPABASE_KEY` (staging project)
- Separate `UPSTASH_REDIS_URL` / `UPSTASH_REDIS_TOKEN` (staging Redis)
- Same `ATTESTATION_SECRET` / `PASSPORT_SIGNING_KEY_V1` (if you want VCs to be cross-environment verifiable)
- `SGRAAL_TEST_MODE` must NOT be set in staging
