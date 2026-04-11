# mnemos-sgraal

Sgraal preflight validation bridge for [mnemos](https://github.com/s60yucca/mnemos).

Validate mnemos agent memories before acting on them.

## Install

```bash
pip install mnemos-sgraal
```

## Usage

```python
from mnemos_sgraal import MnemosSgraal

sgraal = MnemosSgraal("sg_demo_playground", domain="coding")

# Before acting on a recalled memory:
result = sgraal.validate_memory(
    memory_content="JWT uses RS256, tokens expire in 1h",
    action_type="irreversible"
)
print(result["recommended_action"])  # USE_MEMORY / WARN / ASK_USER / BLOCK

# Simple boolean check:
if sgraal.is_safe("Deploy to production — tests passed"):
    # proceed
    pass

# Validate multiple memories at once:
result = sgraal.validate_memories([
    "Database migration completed successfully",
    "API key rotated on 2024-03-15",
    "Cache TTL set to 300 seconds"
])
print(result["recommended_action"])
```
