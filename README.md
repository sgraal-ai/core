# Sgraal

Memory governance protocol for AI agents.

Before an AI agent acts, it should know:
is the memory it's relying on still true?

Sgraal answers that question — in under 10ms.

---

## The problem

AI agents don't know they're forgetting.
They don't know their data is stale.
They don't know two sources contradict each other.
They act anyway — and the mistake only surfaces later.

## What Sgraal does

A single preflight call before every memory-based decision:
```bash
curl -X POST https://api.sgraal.com/v1/preflight \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"memory_state": [...], "action_type": "irreversible", "domain": "fintech"}'
```

Returns:
```json
{
  "omega_mem_final": 42,
  "recommended_action": "USE_MEMORY",
  "assurance_score": 87,
  "explainability_note": "Memory is fresh and consistent."
}
```

`USE_MEMORY` — proceed.  
`WARN` — log and monitor.  
`BLOCK` — stop. Ask. Verify.

---

## Install
```bash
pip install sgraal
npm install @sgraal/mcp
```

## Integrations

- LangGraph
- AutoGen
- Claude (MCP)
- CrewAI

---

## License

Apache 2.0 — open protocol, free to use and embed.

The name comes from *Saint Graal* — because guaranteed  
AI memory is the holy grail of agent systems.
