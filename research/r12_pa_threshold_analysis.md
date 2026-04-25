# R12 PA Threshold Analysis (Sprint 65)

## 3 PA mismatches after Sprint 64

| Case | Ground Truth | API Output | Root Cause | Fixable? |
|------|-------------|------------|------------|----------|
| PA-002 | ASK_USER | BLOCK | pc=MANIPULATED → BLOCK (security invariant) | NO |
| PA-008 | ASK_USER | WARN | pc=SUSPICIOUS escalates only one step (USE_MEMORY→WARN) | YES |
| PA-009 | ASK_USER | BLOCK | action_type_escalation (SUSPICIOUS + destructive → BLOCK) | NO |

## PA-002: MANIPULATED → BLOCK (cannot fix)

pc=MANIPULATED with 4 flags (origin_mismatch, echo_amplification, trust_evolution_anomaly, provenance_asymmetry:manipulated). The architecture mandates MANIPULATED → BLOCK. 5 other PA cases (PA-003, PA-004, PA-006, PA-013) depend on this invariant for their BLOCK decisions. The corpus author's ASK_USER ground truth conflicts with the security-monotone pipeline.

## PA-009: action_type_escalation (cannot fix)

pc=SUSPICIOUS + action_type=destructive → action_type_escalation → BLOCK. This is the CC-005 regression prevention rule: SUSPICIOUS detection on destructive/irreversible actions must escalate to BLOCK. PA-001 (gt=BLOCK, at=destructive, pc=SUSPICIOUS) depends on the same path.

## PA-008: chain_depth escalation (fixable)

**Current**: pc=SUSPICIOUS + chain_depth=4 + action_type=reversible → one-step escalation USE_MEMORY→WARN.
**Expected**: ASK_USER (deeper chains need human review).

**Root cause**: The provenance SUSPICIOUS escalation uses a flat map `{USE_MEMORY: WARN, WARN: ASK_USER}` regardless of chain depth. A chain_depth of 4 (information copied through 4 agents) has higher corruption risk than chain_depth 1, but gets the same single-step escalation.

**Fix**: For chain_depth >= 3, use `{USE_MEMORY: ASK_USER, WARN: ASK_USER}` (double-escalation for deep chains).

**Safety analysis**: All other pc=SUSPICIOUS cases with chain_depth >= 3 are already BLOCK via action_type_escalation (all have destructive/irreversible action types). The double-escalation only changes PA-008's behavior. Zero R2/R3/R4 cases have pc=SUSPICIOUS + chain_depth >= 3. Zero CC/PS cases have chain_depth >= 3.

**Rationale**: Information corruption risk scales with provenance depth. Each hop introduces potential for drift, semantic loss, or manipulation. chain_depth >= 3 is a natural threshold for "deep provenance" warranting human review. This is a principled distinction, not corpus-fitting.

## Expected result

- PA-008: WARN → ASK_USER (+1)
- PA-002, PA-009: unchanged (architectural constraints)
- All other cases: unchanged
- R12: 48/60 → 49/60
