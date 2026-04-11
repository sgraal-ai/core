# bedrock-sgraal

Sgraal preflight validation bridge for [Amazon Bedrock](https://aws.amazon.com/bedrock/).

## Install
```bash
pip install bedrock-sgraal
```

## Usage
```python
from bedrock_sgraal import BedrockSgraal

sgraal = BedrockSgraal("sg_demo_playground", domain="fintech")
if sgraal.is_safe(["retrieved context from Bedrock KB"]):
    # proceed with generation
    pass
```
