# memvid-sgraal

Sgraal preflight validation bridge for [Memvid](https://memvid.com).

Validate Memvid retrieved chunks before passing to LLM.

## Install

```bash
pip install memvid-sgraal
```

## Usage

```python
from memvid_sgraal import MemvidSgraal

sgraal = MemvidSgraal("sg_demo_playground", domain="fintech")

# Validate retrieved chunks before generation:
chunks = ["Revenue grew 12% YoY", "EBITDA margin at 34%", "Debt ratio 0.4"]
result = sgraal.validate_chunks(chunks, action_type="informational")
print(result["recommended_action"])  # USE_MEMORY / WARN / ASK_USER / BLOCK

# Filter — only keep safe chunks:
safe = sgraal.filter_safe_chunks(chunks)

# Structured response for LLM:
response = sgraal.validate_and_chat(chunks, query="Summarize financials")
if response["safe_to_use"]:
    # pass response["chunks"] to LLM
    pass
```
