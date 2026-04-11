# zep-sgraal

Sgraal preflight validation bridge for [Zep](https://www.getzep.com).

## Install
```bash
pip install zep-sgraal
```

## Usage
```python
from zep_sgraal import ZepSgraal

sgraal = ZepSgraal("sg_demo_playground", domain="general")
results = zep_client.memory.search_memory(session_id, query)
if sgraal.is_safe(results):
    pass
```
