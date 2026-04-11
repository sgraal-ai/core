# llamaindex-sgraal

Sgraal preflight validation bridge for [LlamaIndex](https://llamaindex.ai).

## Install

```bash
pip install llamaindex-sgraal
```

## Usage

```python
from llamaindex_sgraal import LlamaIndexSgraal

sgraal = LlamaIndexSgraal("sg_demo_playground", domain="fintech")

# Validate retrieved nodes before generation:
nodes = index.as_retriever().retrieve("What are the compliance requirements?")
if sgraal.is_safe(nodes, action_type="irreversible"):
    response = index.as_query_engine().query("What are the compliance requirements?")
```
