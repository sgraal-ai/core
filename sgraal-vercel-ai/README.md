# vercel-ai-sgraal

Sgraal preflight validation bridge for [Vercel AI SDK](https://sdk.vercel.ai).

## Install
```bash
pip install vercel-ai-sgraal
```

## Usage
```python
from vercel_ai_sgraal import VercelAISgraal

sgraal = VercelAISgraal("sg_demo_playground", domain="general")
if sgraal.is_safe(["user context", "retrieved memory"]):
    # proceed with generation
    pass
```
