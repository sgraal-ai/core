# API Reference

## Overview

The Sgraal API provides memory governance for AI agents. All endpoints are available at `https://api.sgraal.com`.

Interactive documentation: [https://api.sgraal.com/docs](https://api.sgraal.com/docs)
OpenAPI spec: [https://api.sgraal.com/docs/openapi.json](https://api.sgraal.com/docs/openapi.json)

## Authentication

All endpoints (except public ones) require a Bearer token:
```
Authorization: Bearer sg_live_...
```

Get an API key: `POST /v1/signup` with `{"email": "you@company.com"}`

Public endpoints (no auth): `GET /health`, `GET /.well-known/sgraal.json`, `GET /v1/compliance/nist-ai-rmf`, `GET /docs/openapi.json`

## Rate Limiting

Monthly call limits per API key tier:
| Tier | Limit |
|------|-------|
| Free | 10,000 calls/month |
| Starter | 100,000 calls/month |
| Growth | 1,000,000 calls/month |

Returns `429 Too Many Requests` when exceeded.

## Endpoint Groups

### Preflight Scoring
| Method | Path | Description |
|--------|------|-------------|
| POST | /v1/preflight | Score memory state, return decision |
| POST | /v1/preflight/batch | Score up to 100 entries |
| POST | /v1/explain | Human-readable explanation of a result |

### Healing
| Method | Path | Description |
|--------|------|-------------|
| POST | /v1/heal | Heal a single memory entry |
| POST | /v1/heal/batch | Heal multiple entries |
| POST | /v1/outcome | Close an outcome (success/failure) |

### Analytics
| Method | Path | Description |
|--------|------|-------------|
| GET | /v1/analytics/summary | Fleet KPIs |
| GET | /v1/analytics/performance-roi | ROI and savings metrics |
| GET | /v1/audit-log | Audit trail with ETag caching |
| GET | /v1/insights | Agent-level insights |

### Compliance
| Method | Path | Description |
|--------|------|-------------|
| GET | /v1/compliance/nist-ai-rmf | NIST AI RMF controls |
| GET | /v1/compliance/eu-ai-act/report | EU AI Act report |
| GET | /v1/compliance/docs | Compliance documentation |

### Certification
| Method | Path | Description |
|--------|------|-------------|
| POST | /v1/certify | Issue W3C Verifiable Credential |
| POST | /v1/certify/verify | Verify a credential |

### Fleet Intelligence
| Method | Path | Description |
|--------|------|-------------|
| GET | /v1/vaccines | List vaccine signatures |
| GET | /v1/compromised-agents | List flagged agents |
| GET | /v1/fleet/divergence | Diverging agents |

### Configuration
| Method | Path | Description |
|--------|------|-------------|
| POST | /v1/config/thresholds | Set per-domain thresholds |
| GET | /v1/config/thresholds | Get current thresholds |
| POST | /v1/plugins/activate | Activate a plugin |
| GET | /v1/plugins | List plugins |

### Security
| Method | Path | Description |
|--------|------|-------------|
| GET | /v1/security/key-activity | Key anomaly signals |
| POST | /v1/destroy | Destroy memory entries |

### Discovery
| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Dependency health check |
| GET | /.well-known/sgraal.json | Service discovery |
| GET | /docs/openapi.json | OpenAPI spec |

## Key Response Fields (POST /v1/preflight)

| Field | Type | Description |
|-------|------|-------------|
| omega_mem_final | float | Risk score 0-100 |
| recommended_action | string | USE_MEMORY, WARN, ASK_USER, BLOCK |
| assurance_score | float | Confidence in the scoring |
| component_breakdown | dict | Per-component scores (10 components) |
| repair_plan | list | Suggested healing actions |
| decision_trail | list | Every override that fired |
| scoring_warnings | list | Module errors (if any) |
| days_until_block | float | Predicted time to BLOCK |
| governance_score | float | Composite 0-100 governance metric |
| expected_savings_if_blocked | float | Dollar value of this BLOCK |
| early_warning_signals | list | Leading indicators of future BLOCK |
| block_explanation | string | Human-readable BLOCK reason |
| thermodynamic_cost | dict | Landauer energy of this call |

## Error Responses

| Code | Meaning |
|------|---------|
| 400 | Bad request (invalid input) |
| 401 | Invalid API key |
| 403 | Forbidden (demo key scope, wrong tier) |
| 404 | Resource not found |
| 409 | Conflict (outcome already closed) |
| 422 | Validation error (webhook URL, etc.) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
