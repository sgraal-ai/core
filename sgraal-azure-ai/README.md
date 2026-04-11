# azure-ai-sgraal

Sgraal preflight validation bridge for [Azure AI Foundry](https://ai.azure.com).

## Install
```bash
pip install azure-ai-sgraal
```

## Usage
```python
from azure_ai_sgraal import AzureAISgraal

sgraal = AzureAISgraal("sg_demo_playground", domain="fintech")
messages = [{"role": "user", "content": "Execute trade"}, {"role": "assistant", "content": "Processing..."}]
if sgraal.is_safe(messages, action_type="irreversible"):
    pass
```
