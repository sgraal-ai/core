# langfuse-sgraal

Export Sgraal preflight decisions to [Langfuse](https://langfuse.com) as trace spans.

## Install

```bash
pip install langfuse-sgraal
```

## Usage

```python
from langfuse_sgraal import LangfuseSgraal

sgraal = LangfuseSgraal("sg_demo_playground", domain="fintech")

result = sgraal.preflight_with_trace(memory_state=[...], action_type="irreversible")
# result["langfuse_trace"] contains structured trace data for Langfuse SDK
```
