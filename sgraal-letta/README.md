# letta-sgraal

Sgraal preflight validation bridge for [Letta](https://www.letta.com) (formerly MemGPT).

## Install
```bash
pip install letta-sgraal
```

## Usage
```python
from letta_sgraal import LettaSgraal

sgraal = LettaSgraal("sg_demo_playground", domain="coding")
blocks = letta_client.get_agent_memory(agent_id)
if sgraal.is_safe(blocks):
    pass
```
