# sgraal

Memory governance SDK for AI agents. Validates memory state before agent actions using the [Sgraal](https://sgraal.com) preflight protocol.

## Install

```bash
pip install sgraal
```

## Quick Start

```python
from sgraal import SgraalClient

client = SgraalClient(api_key="sg_demo_playground")

result = client.preflight(
    memory_state=[{
        "id": "mem_001",
        "content": "User prefers wire transfers under $10,000",
        "type": "preference",
        "timestamp_age_days": 14,
        "source_trust": 0.91,
        "source_conflict": 0.04,
        "downstream_count": 3
    }],
    domain="fintech",
    action_type="irreversible"
)

action = result["recommended_action"]  # USE_MEMORY | WARN | ASK_USER | BLOCK
omega = result["omega_mem_final"]      # 0-100 risk score

if action == "BLOCK":
    raise RuntimeError(f"Memory too risky: omega={omega}")
```

## MemCube v2 Entry Format

```python
from sgraal import MemoryEntry

entry = MemoryEntry(
    id="mem_001",
    content="Account balance: $50,000",
    type="tool_state",
    timestamp_age_days=3,
    source_trust=0.92,
    source_conflict=0.08,
    downstream_count=5
)

result = client.preflight(
    memory_state=[entry.to_dict()],
    domain="fintech",
    action_type="irreversible"
)
```

## Methods

### `preflight(memory_state, domain, action_type, **kwargs)`
Run a preflight check. Returns omega score, decision, component breakdown, repair plan, and 80+ analytics fields.

### `heal(entry_id, action, agent_id=None)`
Apply a repair action: `REFETCH`, `VERIFY_WITH_SOURCE`, `REBUILD_WORKING_SET`.

### `explain(preflight_result, audience, language)`
Get a natural language explanation. Audiences: `developer`, `compliance`, `executive`.

### `compare_grok(sgraal_decision, grok_decision, omega)`
Compare Sgraal and Grok decisions for the same input.

### `propagation_trace(agent_id, memory_state, domain)`
Trace memory propagation across agents. Returns cascade risk and affected agent count.

### `fidelity_certify(memory_state, domain)`
Certify memory fidelity with a cryptographic proof.

## Demo Key

Use `sg_demo_playground` for testing — no signup needed. Limited to `/v1/preflight` and `/v1/explain`.

## Links

- [sgraal.com](https://sgraal.com) — Landing page
- [app.sgraal.com](https://app.sgraal.com) — Dashboard
- [api.sgraal.com/docs](https://api.sgraal.com/docs) — API docs
- [github.com/sgraal-ai/core](https://github.com/sgraal-ai/core) — Source

## License

Apache 2.0
