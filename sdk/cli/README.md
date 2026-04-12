# sgraal-cli

Sgraal Memory Governance CLI.

## Install
```bash
pip install sgraal-cli
```

## Commands
```bash
sgraal preflight --file memory.jsonl --domain fintech --action irreversible
sgraal score
sgraal verify --signature <sig> --input-hash <hash> --omega 50 --decision USE_MEMORY --request-id <id>
sgraal config init
sgraal config validate
```

## Configuration

Set API key via environment variable or config file:
```bash
export SGRAAL_API_KEY=sg_live_...
# or
mkdir -p ~/.sgraal && echo "api_key: sg_live_..." > ~/.sgraal/config.yml
```
