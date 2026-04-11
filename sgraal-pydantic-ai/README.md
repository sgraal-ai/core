# pydantic-ai-sgraal

Sgraal preflight validation bridge for [Pydantic AI](https://ai.pydantic.dev).

## Install
```bash
pip install pydantic-ai-sgraal
```

## Usage
```python
from pydantic_ai_sgraal import PydanticAISgraal

sgraal = PydanticAISgraal("sg_demo_playground", domain="coding")
messages = [{"content": "Deploy the feature branch"}, {"content": "Tests passed"}]
if sgraal.is_safe(messages, action_type="irreversible"):
    # proceed with agent action
    pass
```
