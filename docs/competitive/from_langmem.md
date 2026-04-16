# Adding Sgraal to LangMem

## What LangMem does well

LangMem is LangChain's dedicated long-term memory product. It solves the hard storage problems — semantic search over large memory stores, hot/cold tiered storage for cost efficiency, namespace isolation, and background consolidation of memories across sessions. Its API makes it straightforward to persist structured and unstructured memories and retrieve them by semantic similarity, giving agents durable recall that survives far beyond a single conversation buffer.

## What Sgraal adds

Sgraal adds a governance layer for the READ decision. LangMem solves storage; Sgraal governs whether a retrieved memory is safe to act on right now. After LangMem returns a ranked list of semantically relevant memories, Sgraal evaluates freshness decay, source conflict, provenance integrity, drift, and interference patterns — then returns `USE_MEMORY`, `WARN`, `ASK_USER`, or `BLOCK`. This is a safety layer, not a storage replacement.

## Migration

```python
from langmem import AsyncClient
from sgraal import SgraalClient

lm = AsyncClient()
sg = SgraalClient(api_key="sg_live_...")

# Before: agent acts on retrieved memories directly
# results = await lm.search(namespace="user_42", query=user_query)

# After: preflight the retrieved set
results = await lm.search(namespace="user_42", query=user_query)
entries = [{"id": r.id, "content": r.value, "type": "semantic",
            "timestamp_age_days": r.age_days, "source_trust": r.score,
            "source_conflict": 0.1} for r in results]
r = sg.preflight(entries, domain="general", action_type="standard")
safe_results = results if r["recommended_action"] != "BLOCK" else []
```

## Key message

You don't replace LangMem's semantic search with Sgraal. You preflight its results. LangMem solves storage; Sgraal governs the READ decision.