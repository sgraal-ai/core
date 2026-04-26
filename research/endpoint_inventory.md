# Endpoint Inventory Methodology (#834)

## Purpose

Track which of the 350+ API endpoints are actually used in production.
Identify dead endpoints for deprecation.

## Mechanism

- Middleware records `endpoint_last_called:{path}` in Redis on every /v1/* request
- TTL: 90 days (rolling window — if an endpoint isn't called for 90 days, the key expires)
- Admin endpoint: `GET /v1/admin/endpoint-inventory` (requires `SGRAAL_ADMIN_TOKEN`)

## Classification

| Status | Criteria |
|---|---|
| active | Called within last 30 days |
| candidate_for_deprecation | Not called in 30-90 days |
| likely_dead | Not called in 90+ days |
| never_called | No record in Redis (either new or truly unused) |

## Usage

```bash
curl -H "Authorization: Bearer $SGRAAL_ADMIN_TOKEN" \
  https://api.sgraal.com/v1/admin/endpoint-inventory | jq '.likely_dead'
```

## Notes

- First 90 days after deployment will show most endpoints as `never_called` — this is expected
- Endpoints called by internal schedulers (stripe retry, snapshots) are tracked via /v1/* paths
- /health and /metrics are excluded (not /v1/ prefixed)
