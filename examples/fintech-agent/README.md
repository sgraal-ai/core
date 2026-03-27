# Fintech Trading Agent

Trading agent with Sgraal preflight on every decision.

## Setup
```bash
cp .env.example .env
# Add your SGRAAL_API_KEY
pip install sgraal
python agent.py
```

## How it works
1. Agent loads memory (market data, risk model, compliance rules)
2. Sgraal preflight scores memory reliability (Omega_MEM)
3. If BLOCK: agent refuses to trade and shows repair plan
4. If USE_MEMORY: agent proceeds with trade execution

## Deploy to Railway
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template)
