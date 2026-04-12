# Sgraal GitHub Action

Run Sgraal preflight checks in CI/CD. Fails the job on BLOCK, warns on WARN.

## Usage

```yaml
# .github/workflows/memory-check.yml
name: Memory Governance

on: [push, pull_request]

jobs:
  sgraal:
    uses: sgraal-ai/core/.github/workflows/sgraal-check.yml@main
    with:
      memory_file: 'memory_state.jsonl'
      domain: 'fintech'
      action_type: 'irreversible'
    secrets:
      SGRAAL_API_KEY: ${{ secrets.SGRAAL_API_KEY }}
```

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `memory_file` | yes | — | Path to JSONL file with memory entries |
| `domain` | no | `general` | general, customer_support, coding, legal, fintech, medical |
| `action_type` | no | `reversible` | informational, reversible, irreversible, destructive |

## Secrets

| Secret | Required | Description |
|---|---|---|
| `SGRAAL_API_KEY` | yes | API key (`sg_demo_playground` for testing) |

## Outputs

| Output | Description |
|---|---|
| `decision` | USE_MEMORY, WARN, ASK_USER, or BLOCK |
| `omega` | Omega risk score (0-100) |
| `attack_surface` | NONE, LOW, MODERATE, HIGH, CRITICAL |

## Behavior

- **BLOCK** → CI job fails with error
- **WARN / ASK_USER** → CI job passes with warning annotation
- **USE_MEMORY** → CI job passes

## Memory File Format

One JSON object per line (JSONL):

```json
{"id": "mem_001", "content": "Customer prefers email", "type": "preference", "timestamp_age_days": 5, "source_trust": 0.9, "source_conflict": 0.05, "downstream_count": 1}
{"id": "mem_002", "content": "Account verified on 2024-01-15", "type": "semantic", "timestamp_age_days": 30, "source_trust": 0.85, "source_conflict": 0.1, "downstream_count": 3}
```
