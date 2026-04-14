# openai-sgraal

Memory governance for OpenAI agents. Validates AI memory before every decision.

## Installation

```bash
pip install openai-sgraal sgraal
```

## Quick Start

```python
from openai_sgraal import OpenAISgraalClient

client = OpenAISgraalClient(
    sgraal_api_key="sg_live_...",
    openai_api_key="sk-..."
)

# Memory-governed completion
result = client.safe_complete(
    messages=[{"role": "user", "content": "Transfer $50,000 to account 1234"}],
    memory=[
        {"id": "bal_1", "content": "Account balance: $120,000", "type": "tool_state",
         "timestamp_age_days": 0.5, "source_trust": 0.95}
    ],
    model="gpt-4o",
    domain="fintech",
    action_type="irreversible"
)
# result.preflight.recommended_action → "USE_MEMORY" or "BLOCK"
```

## OpenAI Assistants API

```python
from openai import OpenAI
from openai_sgraal import preflight_hook

openai = OpenAI()

# Agent memory from your store
agent_memory = [
    {"id": "pref_1", "content": "Client prefers conservative investments",
     "type": "preference", "timestamp_age_days": 30, "source_trust": 0.9,
     "source_conflict": 0.05, "downstream_count": 3},
]

# Run preflight before acting on memory
decision = preflight_hook(
    api_key="sg_live_...",
    memory_state=agent_memory,
    domain="fintech",
    action_type="irreversible"
)

if decision["recommended_action"] == "BLOCK":
    print(f"Memory unsafe: {decision['explainability_note']}")
else:
    # Safe to proceed with assistant
    thread = openai.beta.threads.create()
    openai.beta.threads.messages.create(
        thread_id=thread.id, role="user",
        content="Should I sell my portfolio?"
    )
```

## Function Calling Hook

Validate memory before function execution:

```python
from openai_sgraal import preflight_hook

def execute_tool_call(tool_call, agent_memory):
    decision = preflight_hook(
        api_key="sg_live_...",
        memory_state=agent_memory,
        domain="fintech",
        action_type="irreversible" if tool_call.function.name == "transfer_funds" else "informational"
    )

    if decision["recommended_action"] == "BLOCK":
        return {"error": "Memory governance blocked this action",
                "omega": decision["omega_mem_final"]}

    return call_function(tool_call)
```

## OpenAI Agents SDK

```python
from openai_sgraal import OpenAISgraalClient

client = OpenAISgraalClient(sgraal_api_key="sg_live_...")

# Before each agent step, validate memory
result = client.safe_complete(
    messages=[{"role": "user", "content": "What should I invest in?"}],
    memory=[{"id": "m1", "content": "Risk tolerance: aggressive", "type": "preference",
             "timestamp_age_days": 60, "source_trust": 0.7}],
    domain="fintech", action_type="reversible"
)

if result.blocked:
    print(f"Agent BLOCKED: {result.preflight.explainability_note}")
```

## Response Fields

Every governed call returns Sgraal synthesis fields:

| Field | Description |
|-------|-------------|
| `omega_mem_final` | Risk score 0-100 |
| `recommended_action` | USE_MEMORY / WARN / ASK_USER / BLOCK |
| `days_until_block` | Predicted days until BLOCK threshold |
| `confidence_calibration` | CALIBRATED / OVERCONFIDENT / UNDERCONFIDENT |
| `knowledge_age_days` | Weighted mean age of agent memory |
| `monoculture_risk_level` | LOW / MEDIUM / HIGH |

## Environment Variables

```bash
export SGRAAL_API_KEY=sg_live_...
export OPENAI_API_KEY=sk-...
```

## Links

- [Sgraal Documentation](https://sgraal.com/docs)
- [API Reference](https://api.sgraal.com/docs)
- [Playground](https://sgraal.com/playground)

## License

Apache 2.0
