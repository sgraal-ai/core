# Adding Sgraal to LangChain

## What LangChain does well

LangChain is the most widely adopted LLM orchestration framework in the ecosystem. It excels at rapid prototyping, offers a rich library of integrations with vector stores, LLMs, and tools, and provides a mature set of memory abstractions — `ConversationBufferMemory` for simple chat history, `ConversationSummaryMemory` for compressed recall, and `VectorStoreRetrieverMemory` for retrieval-augmented recall. Its agent toolkit and composability make it an excellent foundation for building LLM-powered applications.

## What Sgraal adds

Sgraal adds a governance layer for memory reliability before the LLM reads it. LangChain gives you memory; Sgraal tells you whether it's safe to USE that memory for the current action. This is not a replacement for LangChain's memory classes — it is a safety layer that sits between `memory.load_memory_variables()` and your agent's next step, returning a decision (`USE_MEMORY`, `WARN`, `ASK_USER`, or `BLOCK`) based on freshness, drift, provenance, and 80+ other signals.

## Migration

```python
from langchain.memory import ConversationBufferMemory
from sgraal import SgraalClient

memory = ConversationBufferMemory()
sg = SgraalClient(api_key="sg_live_...")

# Before: agent reads memory directly
# history = memory.load_memory_variables({})

# After: preflight check
entries = [{"id": m.id, "content": m.content, "type": "episodic",
            "timestamp_age_days": m.age_days, "source_trust": 0.9,
            "source_conflict": 0.1} for m in memory.buffer]
r = sg.preflight(entries, domain="general", action_type="standard")
if r["recommended_action"] != "BLOCK":
    history = memory.load_memory_variables({})
```

## Key message

You don't replace `ConversationBufferMemory` with Sgraal. You preflight it. LangChain stores memory, Sgraal governs it.