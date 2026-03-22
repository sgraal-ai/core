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
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "my-agent",
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

No setup required. Call it directly.

---

## Install
```bash
pip install sgraal
```
```bash
npm install @sgraal/mcp
```

## Integrations

- LangGraph — `OmegaMemCheckpoint` node
- AutoGen — preflight middleware
- Claude MCP — native plugin
- CrewAI — tool guard decorator

---

## The name

*Sgraal* comes from *Saint Graal* — the Holy Grail.  
Because guaranteed AI memory is the holy grail of agent systems.

---

## License

Apache 2.0 — open protocol, free to use and embed.

Built by [sgraal-ai](https://github.com/sgraal-ai) · [sgraal.com](https://sgraal.com)
