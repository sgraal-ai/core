# n8n-nodes-sgraal

n8n community node for [Sgraal](https://sgraal.com) Memory Governance.

## Install

In n8n: Settings → Community Nodes → Install → `n8n-nodes-sgraal`

## Node: Sgraal Memory Governance

Validates AI agent memory before action. Routes to "continue" or "blocked" branch.

### Operations
- **Preflight** — validate memory state
- **Batch** — validate multiple memory states
- **Heal** — heal flagged entries
- **Explain** — get explainability report

### Outputs
- **Continue** — USE_MEMORY or WARN (safe to proceed)
- **Blocked** — BLOCK (stop execution)
