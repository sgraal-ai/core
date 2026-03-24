# langchain-sgraal

LangChain integration for the [Sgraal](https://sgraal.com) memory governance protocol.

## Install

```bash
pip install langchain-sgraal
```

## Quick Start

### As a LangChain Tool

```python
from langchain_sgraal import SgraalMemoryGuard

tool = SgraalMemoryGuard(api_key="sg_live_...")

result = tool.invoke({
    "memory_state": [{
        "id": "mem_001",
        "content": "User prefers metric units",
        "type": "preference",
        "timestamp_age_days": 45,
        "source_trust": 0.9,
        "source_conflict": 0.2,
        "downstream_count": 3,
    }],
    "action_type": "irreversible",
    "domain": "fintech",
})
print(result)
# "SAFE (Ω=12.4): Memory is reliable. Proceed."
# or "BLOCKED (Ω=82.1): High risk. Do NOT proceed."
```

### Use in a LangChain Agent

```python
from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI
from langchain_sgraal import SgraalMemoryGuard

llm = ChatOpenAI(model="gpt-4")
tools = [SgraalMemoryGuard(api_key="sg_live_...")]

agent = initialize_agent(tools, llm, agent=AgentType.OPENAI_FUNCTIONS)
agent.run("Check if the user's address memory is still reliable")
```

### Guard Decorator for LangGraph Nodes

```python
from langchain_sgraal import sgraal_guard

@sgraal_guard(
    memory_state=lambda state: state["memories"],
    action_type="irreversible",
    domain="fintech",
    block_on="BLOCK",
)
def process_trade(state):
    return {"result": execute_trade(state)}
```

### with_preflight Wrapper

```python
from langchain_sgraal import with_preflight

def trade_node(state):
    return execute_trade(state)

safe_trade = with_preflight(
    trade_node,
    get_memory=lambda state: state["memories"],
    action_type="irreversible",
    domain="fintech",
)
```

## Environment Variable

Set `SGRAAL_API_KEY` to avoid passing `api_key` everywhere:

```bash
export SGRAAL_API_KEY=sg_live_...
```

## License

Apache 2.0
