# Adding Sgraal to AutoGen

## What AutoGen does well

AutoGen is Microsoft's open-source framework for building multi-agent conversation systems. It excels at orchestrating multiple AI agents that can collaborate, delegate tasks, and teach each other through structured conversations. Its `ConversableAgent` architecture makes it straightforward to build complex multi-agent workflows where agents maintain context across conversation turns, use tools, and learn from human feedback. AutoGen's teachable agents can accumulate knowledge over time, making it a strong choice for building adaptive multi-agent systems.

## What Sgraal adds

Sgraal sits between AutoGen's memory retrieval and the agent's decision logic. AutoGen handles orchestration and inter-agent communication — it answers *what have my agents learned and how should they collaborate?* Sgraal answers *is the memory state reliable enough to act on right now?* Before an AutoGen agent generates a reply based on accumulated context or taught knowledge, Sgraal scores the memory state against 80+ reliability signals and returns a governance decision. AutoGen continues to own orchestration; Sgraal owns the safety gate.

## Migration

```python
from autogen import ConversableAgent
from sgraal import SgraalClient

sg = SgraalClient(api_key="sg_live_...")

# Before: agent generates reply using its accumulated context
# response = agent.generate_reply(messages=conversation)

# After: preflight the agent's memory before generating a reply
entries = [{"id": f"ctx_{i}", "content": msg["content"], "type": "episodic",
            "timestamp_age_days": 0, "source_trust": 0.8,
            "source_conflict": 0.1, "downstream_count": 1}
           for i, msg in enumerate(conversation)]
r = sg.preflight(entries, domain="general", action_type="reversible")
if r["recommended_action"] != "BLOCK":
    response = agent.generate_reply(messages=conversation)
```

## Key message

You don't replace AutoGen with Sgraal. You preflight it. AutoGen is multi-agent orchestration; Sgraal is the preflight check that sits between AutoGen's accumulated context and your agent's decision logic.

> **Bridge available**: See the [`sgraal-autogen`](../../sgraal-autogen/) bridge SDK for a drop-in integration that wires this pattern into existing AutoGen workflows.
