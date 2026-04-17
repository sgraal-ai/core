# Adding Sgraal to CrewAI

## What CrewAI does well

CrewAI is a role-based multi-agent orchestration framework that models agent collaboration as a crew of specialists with defined roles, goals, and backstories. It excels at task delegation — you define agents (Researcher, Writer, Analyst), assign them tasks with expected outputs, and CrewAI handles the execution order, context passing, and inter-agent delegation. Its process types (sequential, hierarchical) make it natural to model real-world team workflows where agents build on each other's outputs.

## What Sgraal adds

Sgraal sits between CrewAI's task context and the crew's execution. CrewAI handles role assignment and task delegation — it answers *which agent should do what, and in what order?* Sgraal answers *is the context each agent is working with reliable enough to act on?* Before a crew kicks off, Sgraal scores the memory state that will feed into agent decisions and returns a governance decision. CrewAI continues to own orchestration; Sgraal owns the safety gate.

## Migration

```python
from crewai import Crew, Agent, Task
from sgraal import SgraalClient

sg = SgraalClient(api_key="sg_live_...")

# Before: crew kicks off and agents act on their context
# result = crew.kickoff()

# After: preflight the context before crew execution
entries = [{"id": f"task_{i}", "content": task.description, "type": "semantic",
            "timestamp_age_days": 0, "source_trust": 0.85,
            "source_conflict": 0.1, "downstream_count": len(crew.agents)}
           for i, task in enumerate(crew.tasks)]
r = sg.preflight(entries, domain="general", action_type="reversible")
if r["recommended_action"] != "BLOCK":
    result = crew.kickoff()
```

## Key message

You don't replace CrewAI with Sgraal. You preflight it. CrewAI is multi-agent task delegation; Sgraal is the preflight check that sits between CrewAI's task context and your crew's execution.

> **Bridge available**: See the [`sgraal-crewai`](../../sgraal-crewai/) bridge SDK for a drop-in integration that wires this pattern into existing CrewAI workflows.
