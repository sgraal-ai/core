# langsmith-sgraal

Export Sgraal preflight decisions to [LangSmith](https://smith.langchain.com) as trace spans.

## Install

```bash
pip install langsmith-sgraal
```

## Usage

```python
from langsmith_sgraal import LangSmithSgraal

sgraal = LangSmithSgraal("sg_demo_playground", domain="fintech",
                          langsmith_project="my-project")

result = sgraal.preflight_with_trace(memory_state=[...], action_type="irreversible")
# result["langsmith_trace"] contains structured trace data
```
