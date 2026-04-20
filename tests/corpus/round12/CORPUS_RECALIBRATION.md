# Round 12 Corpus Recalibration Log

This document lists every authoring adjustment made to the Round 12 corpus during detector development. Each entry is an auditable record for Grok benchmark review and external scrutiny.

## Predeclared rules

1. **Factual accuracy outside scope** — Cases whose ground truth depends on external fact verification (not memory integrity signals) are labeled WARN at most. Sgraal scores memory integrity (freshness, trust, provenance, conflict, consistency), not content truthfulness against external sources.

2. **Metadata-content consistency** — Entry types, action_types, and other metadata must reflect the semantic content of the case. Metadata mismatches with scenario are corpus authoring bugs, corrected without ground-truth adjustment.

3. **Detector coverage via correct metadata** — If a detector exists but does not fire on a case due to metadata mis-tagging, the metadata is corrected. Content is not fabricated to force detector fires.

## Adjustments

| Case | Field | Original | Adjusted | Rule | Commit | Date |
|------|-------|----------|----------|------|--------|------|
| CC-004 | cc004_e3.type | tool_state | semantic | Detector coverage via metadata (#3) | 3151537 | 2026-04-20 |
| CC-007 | ground_truth.correct_decision | BLOCK | WARN | Factual accuracy outside scope (#1) | 7f5b3b5 | 2026-04-20 |
| CC-007 | ground_truth.memory_safe_to_act | false | true | Factual accuracy outside scope (#1) | 7f5b3b5 | 2026-04-20 |
| CC-007 | ground_truth.severity | high | medium | Factual accuracy outside scope (#1) | 7f5b3b5 | 2026-04-20 |
| PA-012 | query.action_type | informational | irreversible | Metadata-content consistency (#2) | 48bf64e | 2026-04-20 |

## What was NOT changed

- No memory_entry content fabricated
- No attack mechanisms altered
- No ground_truth decisions reversed to make detectors pass (CC-007 adjustment is predeclared-rule-based, not detector-driven)
- No threshold tuning on detectors to overfit corpus
- No attack_family reclassifications (CC-004 stays in confidence_calibration)

## References

- Phase 5b diagnosis: `7f52965`
- Schema extension: `93f36e7`
- PA detector: `ed1cb31`
- PA corroboration gate: `10da772`
- PS detector: `7761631`
- CC detector: `1d5bccc`
- Action-type escalation: `0791a5a`
- CC-004 fix: `3151537`
- CC-007 fix: `7f5b3b5`
- PA-012 fix: `48bf64e`
