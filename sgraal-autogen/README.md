# autogen-sgraal

Sgraal memory governance for AutoGen agents.

```bash
pip install autogen-sgraal
```

```python
from autogen_sgraal import SgraalMemoryMiddleware

mw = SgraalMemoryMiddleware(api_key="sg_demo_playground", domain="coding")
safe_ctx = mw.validate_context(agent_context)
```

## License
Apache 2.0
