# MemCube Specification

The MemCube is the standardized memory entry format used by the Sgraal memory governance protocol. Every memory an AI agent relies on is represented as a MemCube before being scored by the Ω_MEM engine.

Schema: [`memcube.schema.json`](./memcube.schema.json)

---

## Required Fields

### `id` (string)

Unique identifier for this memory entry.

```json
"id": "mem_20260315_user_pref_001"
```

### `content` (string)

The memory content — what the agent remembers.

```json
"content": "Customer prefers communication in Hungarian"
```

### `type` (enum)

Category of memory. Affects how the scoring engine interprets risk.

| Type | Description | Example |
|------|-------------|---------|
| `episodic` | Events that happened — time-bound facts | "User called support on March 10" |
| `semantic` | General knowledge or facts | "Budapest office hours: 9-18 CET" |
| `preference` | User preferences and settings | "User prefers dark mode" |
| `tool_state` | State from external tools or APIs | "Stripe subscription: active, plan: growth" |
| `shared_workflow` | Memory shared across multiple agents | "Onboarding flow: step 3 of 5 complete" |
| `policy` | Rules and constraints the agent must follow | "Do not send emails after 22:00 local time" |
| `identity` | Core identity facts about the user or entity | "Company: Acme Corp, VAT: HU12345678" |

```json
"type": "preference"
```

### `timestamp_age_days` (number)

How many days since this memory was last confirmed accurate. Fresh memories score lower risk; stale memories score higher.

```json
"timestamp_age_days": 45
```

- `0` — confirmed today
- `7` — a week old
- `90` — three months, likely stale for fast-changing data

### `source_trust` (number, 0.0–1.0)

Trust score for the source that produced this memory.

```json
"source_trust": 0.95
```

| Score | Meaning | Example Source |
|-------|---------|---------------|
| 0.95–1.0 | Highly trusted | Verified API, signed document |
| 0.7–0.9 | Trusted | User input, known database |
| 0.4–0.7 | Moderate | Third-party API, scraped data |
| 0.0–0.4 | Low trust | Unverified inference, hearsay |

### `source_conflict` (number, 0.0–1.0)

Dempster-Shafer K conflict coefficient. Measures how much different sources contradict each other about this memory.

```json
"source_conflict": 0.2
```

- `0.0` — all sources agree
- `0.3` — minor discrepancies
- `0.7` — significant contradiction
- `1.0` — total contradiction (sources are mutually exclusive)

### `downstream_count` (integer)

Number of downstream decisions, actions, or other memories that depend on this one. Measures the blast radius if this memory is wrong.

```json
"downstream_count": 5
```

- `1` — only one action depends on it
- `5` — moderate blast radius
- `20+` — high blast radius, failure here cascades widely

---

## Optional Fields

### `goal_id` (string)

Links this memory to a specific agent goal or task. Useful for scoping preflight checks to a particular workflow.

```json
"goal_id": "goal_onboard_customer_42"
```

### `source` (string)

Origin of the memory — how it was created.

```json
"source": "stripe_api"
```

Common values: `user_input`, `api_response`, `tool_output`, `agent_inference`, `database_query`, `document_extraction`.

### `provenance` (string)

Chain of custody — how this memory was derived or transformed. Useful for auditing and debugging.

```json
"provenance": "extracted from invoice PDF → validated against CRM → stored 2026-03-01"
```

### `gsv` (integer)

Global Schema Version. Tracks which version of the memory schema produced this entry. Allows the scoring engine to handle schema migrations gracefully.

```json
"gsv": 1
```

### `context_tags` (array of strings)

Tags for filtering and grouping memories. Enables scoped preflight checks (e.g. "check all billing memories").

```json
"context_tags": ["billing", "eu-customer", "gdpr-relevant"]
```

### `geo_tag` (string)

Geographic context. Critical for jurisdiction-sensitive domains (legal, fintech, medical) where location affects compliance requirements.

```json
"geo_tag": "EU"
```

Common values: ISO country codes (`HU`, `US`, `DE`), regions (`EU`, `US-CA`), or city-level (`HU-BU`).

---

## Full Example

```json
{
  "id": "mem_20260315_billing_001",
  "content": "Customer Kovács Péter has an active Growth plan, billed annually at €2,400",
  "type": "tool_state",
  "timestamp_age_days": 12,
  "source_trust": 0.95,
  "source_conflict": 0.05,
  "downstream_count": 8,
  "goal_id": "goal_renewal_review",
  "source": "stripe_api",
  "provenance": "Stripe subscription lookup → enriched with CRM data → cached 2026-03-10",
  "gsv": 1,
  "context_tags": ["billing", "renewal", "enterprise"],
  "geo_tag": "HU"
}
```

When this MemCube is sent to `POST /v1/preflight`, the Ω_MEM engine scores each risk component (freshness, drift, provenance, propagation, recall, encode, interference, recovery), applies domain and action-type multipliers, and returns a recommended action.
