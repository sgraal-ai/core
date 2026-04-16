# Adding Sgraal to Zep

## What Zep does well

Zep is a memory and knowledge-graph product purpose-built for LLM applications. It excels at extracting structured facts from unstructured conversation, building and maintaining a temporal knowledge graph of entities and relationships, and providing fast semantic and graph-based retrieval. Its fact extraction pipeline and graph model let agents reason over a far richer representation of user and session state than a flat conversation buffer can provide.

## What Zep adds

Zep extracts facts; Sgraal decides whether those facts are safe to act on. Even a high-quality extracted fact can be stale, contradicted by newer information, poorly sourced, or caught in a propagation chain from an unreliable upstream agent. Sgraal evaluates the retrieved facts against freshness decay, provenance integrity, source conflict, drift, interference, and 80+ other governance signals — returning `USE_MEMORY`, `WARN`, `ASK_USER`, or `BLOCK` before your agent commits to an action. Zep owns fact representation; Sgraal owns the act-on-it decision.

## Migration

```python
from zep_python import ZepClient
from sgraal import SgraalClient

zep = ZepClient(api_key="zep_...")
sg = SgraalClient(api_key="sg_live_...")

# Before: agent acts on Zep facts directly
# facts = zep.memory.get_facts(session_id="sess_42")

# After: preflight the extracted facts
facts = zep.memory.get_facts(session_id="sess_42")
entries = [{"id": f.uuid, "content": f.fact, "type": "semantic",
            "timestamp_age_days": f.age_days, "source_trust": f.confidence,
            "source_conflict": 0.1} for f in facts]
r = sg.preflight(entries, domain="general", action_type="standard")
safe_facts = facts if r["recommended_action"] != "BLOCK" else []
```

## Key message

You don't replace Zep's knowledge graph with Sgraal. You preflight the facts it extracts. Zep extracts facts; Sgraal governs whether it is safe to act on them.

> **Already integrated**: See the [`sgraal-zep`](../../sgraal-zep/) bridge SDK for a drop-in wrapper that converts Zep memory and facts into MemCube format and runs preflight automatically.