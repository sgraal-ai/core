# Sgraal Framework-Native Integrations

Drop-in memory governance for LangChain and CrewAI — no separate bridge package needed.

## LangChain

```python
from langchain_native import SgraalMemoryGovernor

# Add as callback — validates every retrieval automatically
llm = ChatOpenAI(callbacks=[SgraalMemoryGovernor("sg_live_...")])

# Raises BlockedMemoryError if retrieved docs fail preflight
```

## CrewAI

```python
from crewai_native import SgraalMemoryMiddleware

middleware = SgraalMemoryMiddleware("sg_live_...", domain="coding")
safe_memories = middleware.validate(agent.memory)  # returns [] if BLOCK
```
