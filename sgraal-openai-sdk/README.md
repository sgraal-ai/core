# openai-sgraal

Sgraal memory governance for OpenAI Agents SDK. Validates message context before completion.

```bash
pip install openai-sgraal
```

```python
from openai_sgraal import OpenAISgraalClient

client = OpenAISgraalClient(sgraal_api_key="sg_demo_playground")
result = client.safe_complete(
    messages=[{"role": "user", "content": "What is my account balance?"}],
    model="gpt-4o", domain="fintech"
)
```

## License
Apache 2.0
