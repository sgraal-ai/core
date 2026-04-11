# sgraal-llm-wrapper

Drop-in wrapper that adds Sgraal preflight validation to any LLM call.

## Install
```bash
pip install sgraal-llm-wrapper
```

## Usage
```python
from llm_wrapper_sgraal import SgraalLLMWrapper

wrapper = SgraalLLMWrapper("sg_demo_playground", domain="fintech")

# Wrap any LLM function:
safe_llm = wrapper.wrap(my_llm_function, action_type="irreversible")
result = safe_llm(prompt="Execute trade", context=["memory1", "memory2"])
# Raises ValueError if BLOCK

# Or use as decorator:
@wrapper.decorator("irreversible")
def my_agent(prompt, context=None):
    return llm.generate(prompt)
```
