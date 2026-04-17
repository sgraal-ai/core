# Adding Sgraal to OpenAI Agents SDK

## What OpenAI Agents SDK does well

The OpenAI Agents SDK is the official framework for building agentic applications with OpenAI models. It provides a clean abstraction for tool calling, agent handoffs, guardrails, and multi-agent orchestration through the Runner interface. Its first-class support for structured outputs, function tools, and agent-to-agent delegation makes it the natural choice for teams already building on OpenAI's API. The SDK handles the loop of model calls, tool execution, and handoffs with minimal boilerplate.

## What Sgraal adds

Sgraal sits between the agent's context and the Runner's execution. The OpenAI Agents SDK handles orchestration and tool calling — it answers *which tools should the agent use and when should it hand off?* Sgraal answers *is the memory state feeding into these decisions reliable enough to act on?* Before the Runner executes an agent turn that depends on accumulated context or retrieved data, Sgraal scores the memory state against 80+ reliability signals and returns a governance decision. The Agents SDK continues to own execution; Sgraal owns the safety gate.

## Migration

```python
from agents import Agent, Runner
from sgraal import SgraalClient

sg = SgraalClient(api_key="sg_live_...")
agent = Agent(name="FinanceBot", instructions="You help with finance.")

# Before: run the agent directly
# result = await Runner.run(agent, input=user_message)

# After: preflight the context before running
entries = [{"id": "ctx_0", "content": user_message, "type": "episodic",
            "timestamp_age_days": 0, "source_trust": 0.85,
            "source_conflict": 0.1, "downstream_count": 1}]
r = sg.preflight(entries, domain="fintech", action_type="irreversible")
if r["recommended_action"] != "BLOCK":
    result = await Runner.run(agent, input=user_message)
```

## Key message

You don't replace the OpenAI Agents SDK with Sgraal. You preflight it. The Agents SDK is agent orchestration; Sgraal is the preflight check that sits between your agent's context and its decision logic.

> **Bridge available**: See the [`sgraal-openai-sdk`](../../sgraal-openai-sdk/) bridge SDK for a drop-in `OpenAIGuard` wrapper that wires this pattern into existing OpenAI Agents workflows.
