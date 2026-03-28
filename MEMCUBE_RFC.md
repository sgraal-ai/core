# MemCube v2 RFC Process

## RFC Lifecycle

```
Draft → Review → Accepted → Implemented
```

## Current RFCs

### RFC-001: MemCube v2 Core Schema
- **Status**: Implemented
- **Version**: 2.0.0
- **Spec**: `GET /v1/standard/memcube-spec`

### Required Fields (7)
| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier |
| content | string | Memory content |
| type | enum | episodic, semantic, preference, tool_state, shared_workflow, policy, identity |
| timestamp_age_days | number | Age in days (0 = fresh) |
| source_trust | number | Trust score 0-1 |
| source_conflict | number | Dempster-Shafer conflict 0-1 |
| downstream_count | integer | Blast radius count |

### Optional Fields (6)
| Field | Type | Description |
|-------|------|-------------|
| goal_id | string | Associated goal |
| source | string | Origin (user_stated, api_response, etc.) |
| provenance | object | Provenance chain |
| gsv | integer | Global State Vector |
| context_tags | array | Semantic tags |
| geo_tag | string | Geographic context |

## Proposing an RFC

1. Open a GitHub issue with `[RFC]` prefix
2. Include: motivation, schema changes, backward compatibility analysis
3. Community review period: 14 days
4. Accepted RFCs get a version bump and implementation timeline

## Versioning

MemCube follows semantic versioning:
- **Major** (3.0.0): Breaking schema changes
- **Minor** (2.1.0): New optional fields
- **Patch** (2.0.1): Clarifications, no schema changes
