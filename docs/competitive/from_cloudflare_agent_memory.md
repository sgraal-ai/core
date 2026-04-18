# Adding Sgraal to Cloudflare Agent Memory

## What Cloudflare Agent Memory does well

Cloudflare Agent Memory is a managed memory service for AI agents, built on Durable Objects and Vectorize. It handles the hard infrastructure problems: memory extraction from conversations (via Llama Scout 17B), deduplication by topic key with version chains, 5-channel hybrid retrieval (full-text, fact-key, raw message, vector, HyDE), and synthesized answers via Nemotron. Each profile is an isolated memory store backed by SQLite with FTS indexing. It runs at the edge, globally, with no infrastructure to manage.

Its ingestion pipeline is particularly strong — 8-check verification, 4-type classification (facts, events, instructions, tasks), deterministic SHA-256 IDs for deduplication, and asynchronous background vectorization. The retrieval pipeline uses Reciprocal Rank Fusion to merge 5 parallel search channels, with fact-key matches weighted highest.

## What Sgraal adds

Cloudflare ensures memories are *stored correctly*. Sgraal ensures memories are *safe to act on*.

These are different guarantees. A memory can be perfectly stored and retrieved — and still be stale, drifted, conflicting with other memories, or part of a poisoning attack. Cloudflare's verification checks structural integrity at ingestion time. Sgraal's preflight checks semantic reliability at action time.

Sgraal adds:
- **Freshness scoring** — Weibull decay curves per memory type (facts decay slowly, tasks decay fast)
- **Drift detection** — 5-method ensemble (KL, Wasserstein, JSD, α-Divergence, MMD)
- **Trust propagation** — how conflicts in one memory affect downstream decisions
- **Attack detection** — 4 independent layers catching timestamp manipulation, identity drift, consensus collapse, and provenance chain attacks
- **Action-aware decisions** — the same memory state gets different risk scores for "read an email" vs "execute a wire transfer"
- **Formal proofs** — Lyapunov stability, Banach contraction, Z3 verification on every decision

## Integration

```bash
pip install cloudflare-sgraal
```

```python
from cloudflare_sgraal import CloudflareSgraalBridge

bridge = CloudflareSgraalBridge(
    cloudflare_account_id="your-account-id",
    cloudflare_api_token="your-cf-token",
    sgraal_api_key="sg_live_...",
)

# One call: recall from Cloudflare + validate through Sgraal
result = bridge.recall_and_validate(
    profile_id="my-project",
    query="What are the deployment credentials?",
    action_type="irreversible",
    domain="coding",
)

if result["safe_to_act"]:
    # Memory passed preflight — safe to use
    credentials = result["synthesized_answer"]
    deploy(credentials)
else:
    # Memory is stale, conflicting, or under attack
    print(f"Blocked: omega={result['sgraal_omega']}")
    print(f"Fix: {result['sgraal_result'].get('repair_plan', [])}")
```

## Architecture

```
Agent → Cloudflare Agent Memory (recall) → cloudflare-sgraal bridge → Sgraal (preflight) → Decision
         stores + retrieves                  converts + validates       scores + detects
```

Cloudflare handles storage, deduplication, retrieval, and synthesis.
Sgraal handles freshness, drift, trust, attack detection, and compliance.

## Type Mapping

Cloudflare classifies memories into 4 types. Sgraal maps them to MemCube types with appropriate decay rates:

| Cloudflare | MemCube | Weibull λ | Half-life |
|-----------|---------|-----------|-----------|
| fact | semantic | 0.01 | ~69 days |
| event | episodic | 0.05 | ~14 days |
| instruction | policy | 0.005 | ~139 days |
| task | tool_state | 0.15 | ~5 days |

Tasks decay fastest because they represent ephemeral operational state. Facts decay slowest because they represent stable knowledge. This matches Cloudflare's own design — tasks are "excluded from the vector index" precisely because they're ephemeral.

## When to validate

Not every recall needs preflight. Use Sgraal when:

- **Irreversible actions** — deploying code, sending payments, modifying production data
- **High-stakes domains** — fintech, medical, legal
- **Multi-agent systems** — memory shared across agents (provenance chain risk)
- **After long gaps** — agent hasn't run in days (memories may have drifted)

Skip preflight when:
- **Read-only queries** — "what color theme does the user prefer?"
- **Fresh memories** — just ingested in the current session
- **Low-stakes actions** — reversible, informational

## Links

- [cloudflare-sgraal on PyPI](https://pypi.org/project/cloudflare-sgraal/)
- [Cloudflare Agent Memory](https://blog.cloudflare.com/introducing-agent-memory/)
- [Sgraal](https://sgraal.com)
- [MemCube Spec](https://github.com/sgraal-ai/core/blob/main/spec/MEMCUBE.md)
