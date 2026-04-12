# Sgraal Zapier / Make.com Integration

Webhook-based integration for Zapier and Make.com.

## Configure

```bash
# Zapier
curl -X POST https://api.sgraal.com/v1/zapier/webhook \
  -H "Authorization: Bearer $SGRAAL_KEY" \
  -d '{"webhook_url": "https://hooks.zapier.com/...", "trigger": "block"}'

# Make.com
curl -X POST https://api.sgraal.com/v1/make/webhook \
  -H "Authorization: Bearer $SGRAAL_KEY" \
  -d '{"webhook_url": "https://hook.us1.make.com/...", "trigger": "block"}'
```

## Triggers
- `block` — fires when preflight returns BLOCK
- `warn` — fires on WARN or BLOCK
- `any` — fires on every preflight call

## Payload
```json
{
  "event": "preflight_complete",
  "recommended_action": "BLOCK",
  "omega_mem_final": 85.0,
  "attack_surface_level": "CRITICAL",
  "domain": "fintech",
  "request_id": "uuid"
}
```
