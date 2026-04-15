# sgraal

Python SDK for the [Sgraal](https://sgraal.com) memory governance protocol.

## Install

```bash
pip install sgraal
```

## Quick Start

```python
from sgraal import SgraalClient

client = SgraalClient(api_key="sg_live_...")
# Or set SGRAAL_API_KEY environment variable

result = client.preflight(
    memory_state=[{
        "id": "mem_001",
        "content": "Customer prefers email communication",
        "type": "preference",
        "timestamp_age_days": 12,
        "source_trust": 0.9,
        "source_conflict": 0.1,
        "downstream_count": 3,
    }],
    action_type="irreversible",
    domain="fintech",
)

print(result["recommended_action"])  # USE_MEMORY, WARN, ASK_USER, or BLOCK
print(result["omega_mem_final"])     # Risk score 0-100
print(result["assurance_score"])     # Confidence score
```

## Sign Up

```python
from sgraal import SgraalClient

# No API key needed for signup
import requests
resp = requests.post("https://api.sgraal.com/v1/signup", json={"email": "you@company.com"})
data = resp.json()
print(data["api_key"])  # Save this — shown only once
```

Or use the client:

```python
from sgraal import SgraalClient

client = SgraalClient.__new__(SgraalClient)
client.api_key = ""
client.base_url = "https://api.sgraal.com"
result = client.signup("you@company.com")
print(result["api_key"])
```

## Guard Decorator

Block or warn before executing functions that depend on memory:

```python
from sgraal import guard

@guard(
    memory_state=[{
        "id": "mem_billing",
        "content": "Customer is on Growth plan",
        "type": "tool_state",
        "timestamp_age_days": 30,
        "source_trust": 0.95,
        "source_conflict": 0.05,
        "downstream_count": 5,
    }],
    action_type="irreversible",
    domain="fintech",
    block_on="BLOCK",
)
def charge_customer(customer_id: str, amount: float):
    """Only runs if memory passes preflight check."""
    process_payment(customer_id, amount)
```

### Dynamic Memory State

Pass a callable that receives the same arguments as the wrapped function:

```python
@guard(
    memory_state=lambda customer_id, amount: fetch_memories(customer_id),
    action_type="irreversible",
    domain="fintech",
    block_on="BLOCK",
)
def charge_customer(customer_id: str, amount: float):
    process_payment(customer_id, amount)
```

### Block Levels

- `block_on="BLOCK"` — only block on BLOCK (default)
- `block_on="ASK_USER"` — block on BLOCK and ASK_USER
- `block_on="WARN"` — block on BLOCK, ASK_USER, and WARN

When blocked, raises `SgraalBlockedError`. WARN and ASK_USER log warnings when not blocked.

```python
from sgraal.guard import SgraalBlockedError

try:
    charge_customer("cus_123", 99.00)
except SgraalBlockedError as e:
    print(f"Blocked: {e.result['block_explanation']}")
```

## LangGraph Integration

```python
from sgraal import SgraalClient

client = SgraalClient()

def preflight_node(state):
    """LangGraph node that checks memory before proceeding."""
    result = client.preflight(
        memory_state=state["memories"],
        action_type=state.get("action_type", "reversible"),
        domain=state.get("domain", "general"),
    )
    if result["recommended_action"] == "BLOCK":
        return {**state, "blocked": True, "reason": result["block_explanation"]}
    return {**state, "blocked": False, "omega_score": result["omega_mem_final"]}
```

## GeminiGuard

```python
from sgraal import GeminiGuard

guard = GeminiGuard(
    sgraal_api_key="sg_live_...",
    gemini_api_key="...",
    model="gemini-1.5-flash",
)

# Automatically checks memory before calling Gemini
# BLOCK → returns block message without calling Gemini
# WARN → adds warning context to Gemini prompt
# USE_MEMORY → calls Gemini normally
response = guard.check_and_generate(
    "What is the user's shipping address?",
    memory_data=[{
        "id": "mem_addr",
        "content": "User address: 123 Main St",
        "type": "preference",
        "timestamp_age_days": 30,
        "source_trust": 0.9,
        "source_conflict": 0.1,
        "downstream_count": 2,
    }],
    action_type="irreversible",
    domain="customer_support",
)
```

Requires: `pip install google-generativeai`

## OpenAIGuard

```python
from sgraal import OpenAIGuard

guard = OpenAIGuard(
    sgraal_api_key="sg_live_...",
    openai_api_key="...",
    model="gpt-4",
)

response = guard.check_and_generate(
    "Summarize the contract terms",
    memory_data=[{
        "id": "mem_contract",
        "content": "Liability capped at €500K",
        "type": "tool_state",
        "timestamp_age_days": 90,
        "source_trust": 0.7,
        "source_conflict": 0.4,
        "downstream_count": 5,
    }],
    action_type="irreversible",
    domain="legal",
)
```

Requires: `pip install openai`

## License

Apache 2.0
