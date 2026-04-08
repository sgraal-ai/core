# Sgraal

> **AI agents act on memory. Sgraal decides if that memory is safe to act on.**

[![API](https://img.shields.io/badge/API-live-brightgreen)](https://api.sgraal.com/health)
[![PyPI](https://img.shields.io/pypi/v/sgraal)](https://pypi.org/project/sgraal/)
[![npm](https://img.shields.io/npm/v/@sgraal/mcp)](https://www.npmjs.com/package/@sgraal/mcp)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-1876%20passing-brightgreen)](#)
[![Benchmark](https://img.shields.io/badge/F1-1.000-gold)](https://sgraal.com/blog/grok-benchmark)
[![Corpus](https://img.shields.io/badge/corpus-239%2F239-brightgreen)](https://github.com/sgraal-ai/core/tree/main/tests)
[![PyPI openai-sgraal](https://img.shields.io/pypi/v/openai-sgraal?label=openai-sgraal)](https://pypi.org/project/openai-sgraal/)
[![PyPI crewai-sgraal](https://img.shields.io/pypi/v/crewai-sgraal?label=crewai-sgraal)](https://pypi.org/project/crewai-sgraal/)
[![PyPI autogen-sgraal](https://img.shields.io/pypi/v/autogen-sgraal?label=autogen-sgraal)](https://pypi.org/project/autogen-sgraal/)
[![PyPI sgraal-rag](https://img.shields.io/pypi/v/sgraal-rag?label=sgraal-rag)](https://pypi.org/project/sgraal-rag/)

---

## What is Sgraal?

Sgraal is a **Memory Governance Protocol** — the execution layer between AI agent memory and AI agent action.

Before every decision, it asks: *is the memory this agent is about to act on still true, safe, and reliable?*

It is **not** a memory store. It is **not** a guardrail. It is **not** an observability tool.

It is the single layer that decides whether an AI agent is allowed to act.
Agent Memory → [SGRAAL] → Agent Action
↓
USE_MEMORY / WARN / ASK_USER / BLOCK

---

## The problem

AI agents don't know they're forgetting.
They don't know their data is stale.
They don't know two sources contradict each other.
They act anyway — and the mistake surfaces too late.

**Sgraal catches this before execution. Every time.**

---

## How it works
```bash
curl -X POST https://api.sgraal.com/v1/preflight \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-fintech-01",
    "memory_state": [{
      "id": "mem_001",
      "content": "Client risk profile is conservative",
      "type": "fact",
      "domain": "fintech",
      "timestamp_age_days": 12
    }],
    "action_type": "irreversible"
  }'
```
```json
{
  "recommended_action": "BLOCK",
  "omega_mem_final": 78.4,
  "assurance_score": 91.2,
  "explainability_note": "Highest risk: s_freshness (82/100). Memory is 12 days old for an irreversible financial action.",
  "repair_plan": [{"action": "REFRESH", "entry_id": "mem_001", "priority": "high"}]
}
```

| Decision | Meaning |
|----------|---------|
| `USE_MEMORY` | Memory is reliable — proceed |
| `WARN` | Proceed with logging — monitor closely |
| `ASK_USER` | Pause — human confirmation required |
| `BLOCK` | Stop — memory is unsafe to act on |

---

## Benchmark Results

Joint benchmark with Grok across 3 adversarial corpora. Independent builds, side-by-side results.

| Corpus | Cases | Sgraal F1 | False Negatives |
|---|---|---|---|
| Sponsored drift | 60 | **1.000** | 0 |
| Subtle drift (0.30–0.55) | 59 | **1.000** | 0 |
| Hallucination | 60 | **1.000** | 0 |
| **Total** | **239** | **1.000** | **0** |

Full breakdown → [sgraal.com/blog/grok-benchmark](https://sgraal.com/blog/grok-benchmark)
Corpus → [tests/](tests/)

---

## Open Standards

Sgraal publishes two open standards:

**MemCube v2** — standardized memory entry schema
`GET https://api.sgraal.com/v1/standard/memcube-spec`

**SMRS v1.0** — formal memory risk score definition (0–100, 10 components)
`GET https://api.sgraal.com/v1/standard/score-definition`

→ [sgraal.com/standard](https://sgraal.com/standard)

---

## Scoring Engine

10 independent risk dimensions combined into a single **omega score (0–100)**:

| Component | What it measures |
|-----------|-----------------|
| `s_freshness` | Memory age decay (Weibull model) |
| `s_drift` | Semantic drift from source (5-method ensemble) |
| `s_provenance` | Source trustworthiness |
| `s_propagation` | Downstream dependency risk |
| `s_interference` | Conflict with other memory entries |
| `s_recovery` | Estimated heal improvement |
| `r_recall` | Recall failure risk |
| `r_encode` | Encoding quality risk |
| `r_belief` | Context window forgetting risk |
| `s_relevance` | Relevance to current action |

**Action multipliers:** informational 0.5× · reversible 1.0× · irreversible 1.5× · financial 2.0× · destructive 2.5×

---

## Capabilities

### 🛡️ Decide
Preflight validation · omega score · assurance score · confidence intervals · component breakdown · causal graph · natural language explanation (EN/DE/FR)

### 🔒 Protect
Write firewall · sleeper detector · poisoning detection · circuit breaker · tamper detection · cross-agent firewall

### ⏱️ Time
Memory Time Machine · counterfactual engine · decision twin · snapshot & restore · temporal rollback

### 🌐 Scale
Multi-agent coordination · memory court · memory commons · cross-LLM translator · memory passport · memory-DNS

### 📋 Comply
EU AI Act · HIPAA · FDA · MiFID2 · Basel IV · GDPR · forensic audit trail · black box logging

### 🔧 Repair
Ranked repair plan · closed-loop heal · autonomous immune system · predictive health · dry-run mode

---

## Quickstart

**Get a free API key** (10,000 calls/month):
```bash
curl -X POST https://api.sgraal.com/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@company.com"}'
```

Or use the **demo key** instantly — no signup:
sg_demo_playground

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
    memory_state=[{"id": "m1", "content": "User prefers metric units", "type": "preference", "timestamp_age_days": 45, "domain": "general"}],
    action_type="irreversible",
)
if result.recommended_action == "BLOCK":
    raise MemoryUnsafeError(result.explainability_note)
```

### Node.js / TypeScript
```bash
npm install @sgraal/mcp
```
```typescript
import { createGuard } from "@sgraal/mcp";
const guard = createGuard();
const result = await guard({
  memory_state: [{ id: "m1", content: "...", type: "fact", timestamp_age_days: 3 }],
  action_type: "reversible",
  domain: "customer_support",
});
```

### Claude Desktop (MCP)
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

### Installation

```bash
# Core Python SDK
pip install sgraal

# Framework integrations
pip install langchain-sgraal   # LangChain
pip install mem0-sgraal        # mem0
pip install openai-sgraal      # OpenAI Agents SDK
pip install crewai-sgraal      # CrewAI
pip install autogen-sgraal     # AutoGen

# RAG pipeline filter
pip install sgraal-rag

# MCP server (Claude Desktop, Cursor, Windsurf)
npm install @sgraal/mcp
```

**Framework integrations:** LangChain · LangGraph · AutoGen · CrewAI · LlamaIndex · mem0 · OpenAI Agents SDK

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

Full docs: [api.sgraal.com/docs](https://api.sgraal.com/docs)

---

## Pricing

| Tier | Price | Included |
|------|-------|----------|
| Free | $0 | 10,000 decisions/month |
| Pro | $0.001/decision | Unlimited |
| Enterprise | Custom | Unlimited + compliance + SLA + support |

---

## The name

*Sgraal* comes from *Saint Graal* — the Holy Grail.
Because truly reliable AI memory is the holy grail of agent systems.

---

## Links

- [sgraal.com](https://sgraal.com) — main site
- [sgraal.com/standard](https://sgraal.com/standard) — open standards
- [sgraal.com/docs](https://sgraal.com/docs) — documentation
- [sgraal.com/blog/grok-benchmark](https://sgraal.com/blog/grok-benchmark) — benchmark blog post
- [api.sgraal.com/docs](https://api.sgraal.com/docs) — API reference
- [pypi.org/project/sgraal](https://pypi.org/project/sgraal) — PyPI
- [npmjs.com/package/@sgraal/mcp](https://npmjs.com/package/@sgraal/mcp) — npm

---

## License

Apache 2.0 — open protocol, free to use, fork, and embed.

Built by [sgraal-ai](https://github.com/sgraal-ai) · [sgraal.com](https://sgraal.com) · [@sgraal_ai](https://x.com/sgraal_ai)
