# R12 Theoretical Ceiling Analysis

## Current state (2026-04-26)
- Live API: 49/60 = 81.7%
- Wilson 95% CI: [70.1%, 89.4%]
- BLOCK preservation: 24/24
- R2 F1: 1.0000
- R3 F1: 1.0000

## Mismatch breakdown (11 cases)

### Architectural invariants — UNFIXABLE without compromising security (2 cases)
- **PA-002**: authored ASK_USER, API outputs BLOCK
  Root cause: MANIPULATED → BLOCK is a hard security invariant. The provenance chain has 4 flags (origin_mismatch, echo_amplification, trust_evolution_anomaly, provenance_asymmetry:manipulated). Fixing this would require allowing manipulated entries to pass through to ASK_USER, which violates the security-monotone pipeline design. 5 other PA cases (PA-003, PA-004, PA-006, PA-013) depend on this invariant for their BLOCK decisions.
- **PA-009**: authored ASK_USER, API outputs BLOCK
  Root cause: SUSPICIOUS + destructive action_type → BLOCK via action_type_escalation. This is the CC-005 lesson from Sprint 64: destructive actions on suspicious memory cannot be downgraded. PA-001 (gt=BLOCK, at=destructive, pc=SUSPICIOUS) depends on the same escalation path.

### Enrichment-driven — fixable with refactor or contradiction detection (5 cases)
- **CC-009, CC-010, CC-012, CC-016, CC-019**
- Root cause: enrichment pipeline inflates omega on structurally ambiguous entries that share metadata signature with R3 attacks. Every guard that helps R12 controls breaks R3 attacks (structurally identical at the enrichment decision point).
- Fixable via:
  * **#763 enrichment refactor** (Sprint 66+ candidate) — separate enrichment paths for entries with vs without provenance metadata
  * **#880 contradiction detection layer** — claim extraction + numerical contradiction (e.g., "$5K threshold" vs "$3K threshold"), not full LLM. Would break the enrichment ceiling by adding a signal that distinguishes benign staleness from active contradiction.

### Semantic-driven — fixable with embedding/LLM capability (4 cases)
- **CC-004, CC-007, CC-008, CC-011**
- Root cause: distinguishing benign content variation from semantic drift requires content interpretation, not metadata analysis. CC-004 is progressive semantic softening ("Changes Requested" → "findings addressed" → "approved"). CC-008 is correlated confidence without contradicting content. These cases are structurally sound — the attack is in the meaning, not the metadata.
- Fixable via:
  * **#19 Open-source LLM Sentinel** — lightweight local model for semantic consistency checking
  * **#486 LLM-based semantic importance scoring** — content-aware scoring component
  * **#761, #820 NL explanation generator** — side effect of building content understanding

## Theoretical ceilings

| Scenario | R12 score | % | Wilson 95% CI |
|---|---|---|---|
| Current | 49/60 | 81.7% | [70.1%, 89.4%] |
| + contradiction detection (#880) | 54/60 | 90.0% | [79.9%, 95.3%] |
| + contradiction + enrichment refactor (#763) | 54/60 | 90.0% | [79.9%, 95.3%] |
| + contradiction + enrichment + semantic (LLM) | 58/60 | 96.7% | [88.6%, 99.1%] |
| **Absolute architectural maximum** | **58/60** | **96.7%** | **[88.6%, 99.1%]** |

Note: contradiction detection and enrichment refactor address the same 5 CC cases from different angles. They don't stack — either approach fixes the same cases. The maximum from both combined is still 54/60.

## Pitch usage

Honest framing options:
- "R12 = 49/60 = 81.7% with 95% CI [70.1%, 89.4%]. Architectural maximum is 58/60 = 96.7%."
- "Of 11 remaining mismatches, 2 are architectural invariants — security overrides authored ground truth. Fixing them would compromise the security model."
- "Closing the gap from 49 to 58 requires contradiction detection + semantic understanding. Both on roadmap (#880, #19)."
- "24/24 BLOCK = 100% with 95% CI [86.2%, 100.0%] — zero false negatives on high-severity attacks."

## Honest framing — defensible argument

The presence of architectural invariants is a *feature*, not a bug:

1. PA-002 and PA-009 prove the system applies consistent safety rules over corpus-fitting. A system that relaxes MANIPULATED → BLOCK to match authored ground truth on 2 cases would lose BLOCK preservation on real attacks.
2. The CC-005 regression during Sprint 64 proved this concretely: suppressing action_type_escalation for self-authored entries caused a genuine attack case (CC-005) to drop from BLOCK to ASK_USER. The fix was immediate revert — architectural invariants are load-bearing.
3. The gap between 49/60 and 58/60 represents capabilities the roadmap explicitly addresses (enrichment refactor + semantic understanding), not threshold tuning. Every improvement from 43 → 49 was principled: self-authored derivation (#783), sync-aware detection (#822), deep chain escalation (Sprint 65), PA schema fix — none were corpus-fitting.

## Wilson confidence interval calculation reference

```python
from statsmodels.stats.proportion import proportion_confint
ci = proportion_confint(49, 60, alpha=0.05, method='wilson')
# (0.7005, 0.8944)

ci = proportion_confint(54, 60, alpha=0.05, method='wilson')
# (0.7992, 0.9534)

ci = proportion_confint(58, 60, alpha=0.05, method='wilson')
# (0.8860, 0.9914)
```
