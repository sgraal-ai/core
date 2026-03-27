# Sgraal Memory Emulator

Drop-in replacement for memory provider APIs with built-in Sgraal governance.

## Quick Start

```bash
# Emulate Mem0 API with Sgraal preflight on every write/search
sgraal emulate --provider mem0 --port 8080 --api-key sg_live_...

# Dry run — see decisions without calling Sgraal API
sgraal emulate --provider mem0 --port 8080 --api-key sg_live_... --dry-run

# Debug logging
sgraal emulate --provider mem0 --port 8080 --api-key sg_live_... --log-level debug
```

## Supported Providers

| Provider | Status | Emulated Endpoints |
|----------|--------|-------------------|
| **mem0** | Supported | POST /v1/memories, POST /v1/memories/search, DELETE /v1/memories/{id} |
| zep | Planned | Returns 501 |
| letta | Planned | Returns 501 |

## How It Works

1. **POST /v1/memories** — Stores memory, runs Sgraal preflight. BLOCK = 409 rejection.
2. **POST /v1/memories/search** — Returns memories filtered by Sgraal risk score (omega > 80 = filtered).
3. **DELETE /v1/memories/{id}** — Direct delete.

Response format matches Mem0 API with additional `sgraal` field.

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--provider` | required | mem0, zep, letta |
| `--port` | 8080 | Server port |
| `--api-key` | required | Sgraal API key |
| `--api-url` | api.sgraal.com | Sgraal API URL |
| `--dry-run` | false | Show decisions without API calls |
| `--log-level` | info | debug, info, warning, error |
