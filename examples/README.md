# Sgraal Example Projects

Production-ready examples of AI agents with Sgraal memory governance.

| Example | Stack | Domain | Description |
|---------|-------|--------|-------------|
| [fintech-agent](./fintech-agent/) | Python, LangGraph | Fintech | Trading agent with preflight on every decision |
| [support-agent](./support-agent/) | Node.js | Customer Support | Support agent with memory quality monitoring |
| [medical-copilot](./medical-copilot/) | Python | Healthcare | HIPAA-compliant medical assistant |
| [coding-agent](./coding-agent/) | Python | Coding | Coding assistant with @guard decorator |
| [mem0-migration](./mem0-migration/) | Python | General | Migrate Mem0 → mem0-sgraal in 5 minutes |

## Quick Start

```bash
cd fintech-agent
cp .env.example .env
# Add your SGRAAL_API_KEY
pip install -r requirements.txt
python agent.py
```

## Get an API Key

```bash
curl -X POST https://api.sgraal.com/v1/signup -d '{"email": "you@example.com"}'
```

Or sign up at [sgraal.com](https://sgraal.com).
