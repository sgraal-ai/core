# Adding Sgraal to Mem0

## What Mem0 does well

Mem0 is a popular open-source memory layer providing persistent memory across sessions for LLM agents. It handles the operationally hard parts of agent memory — automatic extraction of facts and preferences from raw conversation, user-scoped and agent-scoped namespaces, vector-backed retrieval, and managed persistence so that memories survive across process restarts and long time horizons. Its `add()` / `search()` API makes it simple to give agents continuity across sessions.

## What Sgraal adds

Sgraal sits between Mem0 and your agent's decision logic. Mem0 is memory-as-a-service — it answers *what do we remember about this user?* Sgraal answers *should we act on it right now?* Before your agent reads a Mem0 result and makes a decision (especially an irreversible or destructive one), Sgraal scores the retrieved memory state against 80+ reliability signals and returns a governance decision. Mem0 continues to own storage; Sgraal owns the safety gate.

## Migration

```python
from mem0 import Memory
from sgraal import SgraalClient

m = Memory()
sg = SgraalClient(api_key="sg_live_...")

# Before: agent acts on Mem0 results directly
# memories = m.search(query=user_query, user_id="user_42")

# After: preflight the retrieved memories
memories = m.search(query=user_query, user_id="user_42")
entries = [{"id": x["id"], "content": x["memory"], "type": "semantic",
            "timestamp_age_days": x.get("age_days", 0), "source_trust": x.get("score", 0.8),
            "source_conflict": 0.1} for x in memories]
r = sg.preflight(entries, domain="general", action_type="standard")
safe_memories = memories if r["recommended_action"] != "BLOCK" else []
```

## Key message

You don't replace Mem0 with Sgraal. You preflight it. Mem0 is memory-as-a-service; Sgraal is the preflight check that sits between Mem0 and your agent's decision logic.

> **Already integrated**: See the [`mem0-sgraal`](../../sdk/mem0_bridge/) bridge SDK for a drop-in `SafeMemory` wrapper that wires this pattern into existing Mem0 code with no manual entry construction.