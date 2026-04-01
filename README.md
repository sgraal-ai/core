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
      "type": "preference",
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

## Quickstart

Get a free API key (10,000 decisions/month):
```bash
curl -X POST https://api.sgraal.com/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@company.com"}'
```

---

## SDKs & Integrations

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
        "domain": "general",
    }],
    action_type="irreversible",
)

if result.recommended_action == "BLOCK":
    raise MemoryUnsafeError(result.explainability_note)
```

Guard decorator:
```python
from sgraal import guard

@guard(memory_state=[...], action_type="irreversible", domain="fintech")
def execute_trade(symbol, amount):
    # Only runs if memory is safe
    broker.place_order(symbol, amount)
```

### Node.js / TypeScript
```bash
npm install @sgraal/mcp
```
```typescript
import { createGuard } from "@sgraal/mcp";

const guard = createGuard(); // reads SGRAAL_API_KEY from env

const result = await guard({
  memory_state: [{ id: "m1", content: "...", type: "fact", timestamp_age_days: 3 }],
  action_type: "reversible",
  domain: "customer_support",
});
// Throws SgraalBlockedError on BLOCK
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

### Other SDKs
| Language | Install |
|----------|---------|
| Go | `go get github.com/sgraal-ai/sgraal-go` |
| Java | `maven: com.sgraal:sgraal-java` |
| Rust | `cargo add sgraal` |
| C# | `dotnet add package Sgraal` |

### Framework Integrations
LangChain · LangGraph · AutoGen · CrewAI · LlamaIndex · Semantic Kernel · Haystack · Flowise · n8n · Zapier · Claude Desktop · Cursor · Replit · any REST client

---

## REST API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/preflight` | POST | Core decision endpoint |
| `/v1/explain` | POST | Natural language explanation |
| `/v1/heal` | POST | Repair memory entries |
| `/v1/store/memories` | POST | Store memory entry |
| `/v1/memory/graph` | GET | Memory relationship graph |
| `/v1/audit-log` | GET | Decision audit trail |
| `/v1/analytics/summary` | GET | Fleet analytics |
| `/v1/sla/report` | GET | SLA metrics |
| `/v1/compliance/report` | POST | Regulatory compliance report |

Full API docs: [api.sgraal.com/docs](https://api.sgraal.com/docs)

---

## Pricing

| Tier | Price | Included |
|------|-------|----------|
| Free | $0 | 10,000 decisions/month |
| Pro | $0.001/decision | Unlimited |
| Enterprise | Custom | Unlimited + compliance + SLA + support |

---

## Live Infrastructure

| Service | URL | Status |
|---------|-----|--------|
| API | [api.sgraal.com](https://api.sgraal.com) | ✅ Live |
| Dashboard | [app.sgraal.com](https://app.sgraal.com) | ✅ Live |
| Docs | [api.sgraal.com/docs](https://api.sgraal.com/docs) | ✅ Live |
| Landing | [sgraal.com](https://sgraal.com) | ✅ Live |

---

## The name

*Sgraal* comes from *Saint Graal* — the Holy Grail.

Because truly reliable AI memory is the holy grail of agent systems.

---

## License

Apache 2.0 — open protocol, free to use, fork, and embed.

Built by [sgraal-ai](https://github.com/sgraal-ai) · [sgraal.com](https://sgraal.com) · [@sgraal_ai](https://x.com/sgraal_ai)
