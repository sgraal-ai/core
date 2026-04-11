# .sgraal Configuration Format

Version: 1.0

A `.sgraal` file defines agent memory governance policy. Place it in your project root or pass via the `/v1/policy/apply` endpoint.

## Schema

```json
{
  "version": "1.0",
  "agent_id": "my-agent-001",
  "domain": "fintech",
  "default_action_type": "reversible",
  "thresholds": {
    "block_omega": 70,
    "warn_omega": 40,
    "ask_user_omega": 55
  },
  "detection": {
    "timestamp_integrity": true,
    "identity_drift": true,
    "consensus_collapse": true,
    "provenance_chain": true,
    "naturalness_score": true
  },
  "response_profile": "standard",
  "block_on_suspicious": false,
  "trusted_agents": ["agent-planner-01", "agent-summarizer-03"],
  "blocked_agents": ["agent-compromised-99"]
}
```

## Fields

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| version | string | yes | — | Config version. Currently "1.0" |
| agent_id | string | yes | — | Agent identifier |
| domain | string | yes | — | general, customer_support, coding, legal, fintech, medical |
| default_action_type | string | no | "reversible" | informational, reversible, irreversible, destructive |
| thresholds | object | no | defaults | Custom omega thresholds |
| detection | object | no | all true | Enable/disable detection layers |
| response_profile | string | no | auto | compact or standard |
| block_on_suspicious | bool | no | false | Force BLOCK on any SUSPICIOUS detection |
| trusted_agents | array | no | [] | Agent IDs to trust in provenance chain |
| blocked_agents | array | no | [] | Agent IDs to always reject |

## Validation

```bash
curl -X POST https://api.sgraal.com/v1/policy/validate \
  -H "Authorization: Bearer sg_demo_playground" \
  -H "Content-Type: application/json" \
  -d '{"config": {"version": "1.0", "agent_id": "test", "domain": "general"}}'
```

## Apply to preflight

```bash
curl -X POST https://api.sgraal.com/v1/policy/apply \
  -H "Authorization: Bearer sg_demo_playground" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {"version": "1.0", "agent_id": "test", "domain": "fintech"},
    "memory_state": [{"id": "m1", "content": "test", "type": "semantic", "timestamp_age_days": 5, "source_trust": 0.9}],
    "action_type": "reversible"
  }'
```
