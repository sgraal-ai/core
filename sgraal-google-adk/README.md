# google-adk-sgraal

Sgraal preflight validation bridge for [Google Agent Development Kit](https://google.github.io/adk-docs/).

## Install
```bash
pip install google-adk-sgraal
```

## Usage
```python
from google_adk_sgraal import GoogleADKSgraal

sgraal = GoogleADKSgraal("sg_demo_playground", domain="fintech")
state = {"user_id": "123", "balance": "45000", "pending_trade": "BUY 100 AAPL"}
if sgraal.is_safe(state, action_type="irreversible"):
    # execute trade
    pass
```
