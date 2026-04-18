# cloudflare-sgraal

**Cloudflare stores it. Sgraal validates it.**

Sgraal preflight guard for [Cloudflare Agent Memory](https://blog.cloudflare.com/introducing-agent-memory/). Validates recalled memories before your agent acts on them.

```
pip install cloudflare-sgraal
```

## Quick Start

```python
from cloudflare_sgraal import CloudflareSgraalBridge

bridge = CloudflareSgraalBridge(
    cloudflare_account_id="your-account-id",
    cloudflare_api_token="your-cf-token",
    sgraal_api_key="sg_live_...",
)

# Recall from Cloudflare + validate through Sgraal
result = bridge.recall_and_validate(
    profile_id="my-project",
    query="What package manager does the user prefer?",
    action_type="reversible",
    domain="coding",
)

if result["safe_to_act"]:
    print(result["synthesized_answer"])
else:
    print(f"Blocked: omega={result['sgraal_omega']}")
    print(f"Repair: {result['sgraal_result'].get('repair_plan', [])}")
```

## What It Does

1. **Recalls** memories from Cloudflare Agent Memory via REST API
2. **Converts** Cloudflare entries (fact/event/instruction/task) to MemCube format
3. **Validates** through Sgraal preflight (hallucination detection, drift, trust scoring)
4. **Returns** combined result with `safe_to_act` boolean

## Type Mapping

| Cloudflare Type | MemCube Type | Decay Rate |
|----------------|-------------|------------|
| fact | semantic | Slow (λ=0.01) |
| event | episodic | Moderate (λ=0.05) |
| instruction | policy | Very slow (λ=0.005) |
| task | tool_state | Fast (λ=0.15) |

## Block Handling

```python
# Raise exception on BLOCK (default — safest)
bridge = CloudflareSgraalBridge(..., on_block="raise")

# Warn but return memories
bridge = CloudflareSgraalBridge(..., on_block="warn")

# Silently pass — caller checks sgraal_decision
bridge = CloudflareSgraalBridge(..., on_block="pass")
```

## Validate Pre-Fetched Memories

If you already have memories from Cloudflare's Worker binding:

```python
# From your Cloudflare Worker (JS/TS):
# const results = await profile.recall("query");
# Pass results.memories to Python via API

result = bridge.validate_memories(
    memories=worker_memories,
    action_type="irreversible",
    domain="fintech",
)
```

## Response Shape

```python
{
    "cloudflare_memories": [...],       # Raw Cloudflare entries
    "synthesized_answer": "pnpm",       # Cloudflare's synthesized answer
    "memory_state": [...],              # MemCube-converted entries
    "sgraal_decision": "USE_MEMORY",    # USE_MEMORY | WARN | ASK_USER | BLOCK
    "sgraal_omega": 12.3,              # Risk score (0=safe, 100=dangerous)
    "sgraal_result": {...},            # Full Sgraal preflight response
    "safe_to_act": True,               # Convenience: decision in (USE_MEMORY, WARN)
}
```

## Links

- [Sgraal](https://sgraal.com) — Memory governance protocol
- [Cloudflare Agent Memory](https://blog.cloudflare.com/introducing-agent-memory/) — Managed memory for AI agents
- [Sgraal Python SDK](https://pypi.org/project/sgraal/) — Core SDK
- [GitHub](https://github.com/sgraal-ai/core)
