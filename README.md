# Sgraal

**Memory governance protocol for AI agents.**

Before an AI agent acts, it should know:  
*is the memory it's relying on still true?*

Sgraal answers that question — in under 10ms.

---

## The problem

AI agents don't know they're forgetting.  
They don't know their data is stale.  
They don't know two sources contradict each other.  
They act anyway — and the mistake only surfaces later.

## How it works

A single preflight call before every memory-based decision:
```bash
curl -X POST https://api.sgraal.com/v1/preflight \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "memory_state": [{
      "id": "entry_001",
      "content": "User prefers email communication",
      "type": "preference_memory",
      "timestamp_age_days": 3,
      "source_trust": 0.95,
      "source_conflict": 0.05,
      "downstream_count": 2
    }],
    "action_type": "reversible",
    "domain": "customer_support"
  }'
```

Returns:
```json
{
  "omega_mem_final": 18,
  "recommended_action": "USE_MEMORY",
  "assurance_score": 87,
  "explainability_note": "Highest risk: s_freshness (15.0/100). Action: USE_MEMORY.",
  "component_breakdown": {
    "s_freshness": 15,
    "s_drift": 9,
    "s_provenance": 5,
    "s_propagation": 8,
    "r_recall": 11,
    "r_encode": 2,
    "s_interference": 5,
    "s_recovery": 92
  }
}
```

| Decision | Meaning |
|----------|---------|
| `USE_MEMORY` | Proceed — memory is reliable |
| `WARN` | Log and monitor |
| `ASK_USER` | Confirm before acting |
| `BLOCK` | Stop — memory is unsafe |

---

## Live API
```
https://api.sgraal.com/v1/preflight
https://api.sgraal.com/health
https://api.sgraal.com/docs
```

## Quickstart

Sign up for a free API key (10,000 calls/month):
```bash
curl -X POST https://api.sgraal.com/v1/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "you@company.com"}'
```

---

## Install

### REST API

No SDK needed — call directly from any language:
```bash
curl -X POST https://api.sgraal.com/v1/preflight \
  -H "Authorization: Bearer sg_live_..." \
  -H "Content-Type: application/json" \
  -d '{"memory_state": [...], "action_type": "reversible", "domain": "general"}'
```

### Python

```bash
pip install sgraal
```

```python
from sgraal import SgraalClient

client = SgraalClient(api_key="sg_live_...")

result = client.preflight(
    memory_state=[{
        "id": "mem_001",
        "content": "User prefers metric units",
        "type": "preference",
        "timestamp_age_days": 45,
        "source_trust": 0.9,
        "source_conflict": 0.2,
        "downstream_count": 3,
    }],
    action_type="irreversible",
    domain="fintech",
)
print(result.recommended_action)  # USE_MEMORY, WARN, ASK_USER, or BLOCK
```

Guard decorator:
```python
from sgraal import guard

@guard(memory_state=[...], action_type="irreversible", domain="fintech", block_on="BLOCK")
def charge_customer(customer_id, amount):
    process_payment(customer_id, amount)
```

### Node.js / LangGraph

```bash
npm install @sgraal/mcp
```

```typescript
import { createGuard } from "@sgraal/mcp";

const guard = createGuard(); // reads SGRAAL_API_KEY from env

const result = await guard({
  memory_state: [{
    id: "mem_001",
    content: "User prefers metric units",
    type: "preference",
    timestamp_age_days: 45,
    source_trust: 0.9,
    source_conflict: 0.2,
    downstream_count: 3,
  }],
  action_type: "irreversible",
  domain: "fintech",
});
// Throws SgraalBlockedError on BLOCK
// Logs warning on WARN
// Passes through on USE_MEMORY
```

### Claude Desktop (MCP)

```bash
npm install @sgraal/mcp
```

Add to `claude_desktop_config.json`:
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

## Integrations

- **REST API** — any language, no SDK required
- **Python** — `pip install sgraal` with `SgraalClient` and `@guard` decorator
- **Node.js / LangGraph** — `npm install @sgraal/mcp` with `createGuard()` and `withPreflight()`
- **Claude Desktop** — MCP server via `npx @sgraal/mcp`
- **AutoGen** — preflight middleware
- **CrewAI** — tool guard decorator

---

## The name

*Sgraal* comes from *Saint Graal* — the Holy Grail.  
Because guaranteed AI memory is the holy grail of agent systems.

---

## License

Apache 2.0 — open protocol, free to use and embed.

Built by [sgraal-ai](https://github.com/sgraal-ai) · [sgraal.com](https://sgraal.com)

