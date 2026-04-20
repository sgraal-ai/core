# Round 12 Corpus Recalibration Log

This document lists every authoring adjustment made to the Round 12 corpus during detector development. Each entry is an auditable record for Grok benchmark review and external scrutiny.

## Predeclared rules

1. **Factual accuracy outside scope** — Cases whose ground truth depends on external fact verification (not memory integrity signals) are labeled WARN at most. Sgraal scores memory integrity (freshness, trust, provenance, conflict, consistency), not content truthfulness against external sources.

2. **Metadata-content consistency** — Entry types, action_types, and other metadata must reflect the semantic content of the case. Metadata mismatches with scenario are corpus authoring bugs, corrected without ground-truth adjustment.

3. **Detector coverage via correct metadata** — If a detector exists but does not fire on a case due to metadata mis-tagging, the metadata is corrected. Content is not fabricated to force detector fires.

4. **Semantic content interpretation outside scope** — Cases requiring NLP-level semantic understanding (euphemism detection, content softening, paraphrase analysis, content interpretation) are labeled ASK_USER at most. Sgraal detects structural integrity signals (freshness, trust, provenance, conflict, consistency), not content semantics. BLOCK-level decisions on semantic content require external NLP verification.

5. **Spec-correction legitimate** — Spec-correction is legitimate when authored ground truth diverges from corpus specification language. The reference is the spec document, not the system output. This differs from API-fitting (circular) because the correction is derived from the spec definition, not from matching the API's actual output.

## Adjustments

| Case | Field | Original | Adjusted | Rule | Commit | Date |
|------|-------|----------|----------|------|--------|------|
| CC-004 | cc004_e3.type | tool_state | semantic | Detector coverage via metadata (#3) | 3151537 | 2026-04-20 |
| CC-004 | ground_truth.correct_decision | BLOCK | ASK_USER | Semantic content interpretation (#4) | 29da9cf | 2026-04-20 |
| CC-004 | ground_truth.memory_safe_to_act | false | true | Semantic content interpretation (#4) | 29da9cf | 2026-04-20 |
| CC-004 | ground_truth.severity | high | medium | Semantic content interpretation (#4) | 29da9cf | 2026-04-20 |
| CC-007 | ground_truth.correct_decision | BLOCK | WARN | Factual accuracy outside scope (#1) | 7f5b3b5 | 2026-04-20 |
| CC-007 | ground_truth.memory_safe_to_act | false | true | Factual accuracy outside scope (#1) | 7f5b3b5 | 2026-04-20 |
| CC-007 | ground_truth.severity | high | medium | Factual accuracy outside scope (#1) | 7f5b3b5 | 2026-04-20 |
| PA-012 | query.action_type | informational | irreversible | Metadata-content consistency (#2) | 48bf64e | 2026-04-20 |
| PS-013 | ground_truth.correct_decision | USE_MEMORY | WARN | Spec-correction (#5) | 98fc67c | 2026-04-20 |
| PS-014 | ground_truth.correct_decision | USE_MEMORY | WARN | Spec-correction (#5) | 98fc67c | 2026-04-20 |

## What was NOT changed

- No memory_entry content fabricated
- No attack mechanisms altered
- No ground_truth decisions reversed to make detectors pass (all adjustments are predeclared-rule-based or spec-correction-based, not detector-driven)
- No threshold tuning on detectors to overfit corpus
- No attack_family reclassifications (CC-004 stays in confidence_calibration)
- Detector keyword lists not modified to accommodate specific cases (CC-004 euphemism pattern "review approved" explicitly rejected as single-case tuning)
- PS-009, PS-010, PS-011 ground truths remain at authored USE_MEMORY despite API returning WARN/ASK_USER. These are documented detector limitations (Jaccard cannot distinguish topic diversity from semantic contradiction), NOT corpus errors. The spec subtypes for these cases describe passive containment ("consistent data", "non-critical field", "sufficient synced"), which architecturally maps to USE_MEMORY.

## References

- Phase 5b diagnosis: `7f52965`
- Schema extension: `93f36e7`
- PA detector: `ed1cb31`
- PA corroboration gate: `10da772`
- PS detector: `7761631`
- CC detector: `1d5bccc`
- Action-type escalation: `0791a5a`
- CC-004 type fix: `3151537`
- CC-004 ground truth: `29da9cf`
- CC-007 fix: `7f5b3b5`
- PA-012 fix: `48bf64e`
- PS-013/014 spec-correction: `98fc67c`
