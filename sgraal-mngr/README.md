# mngr-sgraal

Sgraal preflight validation bridge for [mngr](https://github.com/imbue-ai/mngr) (Imbue).

Validate inter-agent memory in parallel agent workflows.

## Install

```bash
pip install mngr-sgraal
```

## Usage

```python
from mngr_sgraal import MngrSgraal

sgraal = MngrSgraal("sg_demo_playground", domain="coding")

# Validate single agent output:
if sgraal.is_safe("agent-coder-01", "Refactored auth module"):
    pass  # safe to pass to next agent

# Validate parallel outputs for consensus collapse:
result = sgraal.validate_parallel_outputs({
    "agent-01": "Tests passed for feature X",
    "agent-02": "Code review approved for feature X",
    "agent-03": "Deployment ready for feature X",
})
print(result["consensus_collapse"])  # CLEAN / SUSPICIOUS / MANIPULATED
```
