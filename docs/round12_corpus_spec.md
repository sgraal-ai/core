# Round 12 — Emergent Consensus Attack Corpus Specification

## Overview
Round 12 tests 3 emergent consensus attack vectors that exploit calibration gaps, partial synchronization delays, and multi-hop provenance asymmetry. These attacks are designed to bypass detection layers that assume independent corroboration, complete sync, and transparent provenance.

## Attack Families

### 1. Confidence Calibration (CC)
Exploits the gap between model confidence and actual reliability. Overconfident attacks present stale/false memories with high internal consistency. Underconfident anomalies present true memories that look suspicious.

### 2. Partial-Sync Bleed (PS)
Exploits temporal gaps in multi-agent memory synchronization. When agents sync at different times, stale replicas can outvote fresh corrections, and corrections may reach planners but not executors.

### 3. Multi-hop Provenance Asymmetry (PA)
Exploits trust erosion and identity rebinding across 3+ provenance hops. Source compression, authority aliasing, and normalization can hide the actual origin of a memory.

## Case Schema

Each case is a JSON object with these fields:

- `case_id` (string): R12-{family}-{NNN}
- `round` (int): 12
- `title` (string): Human-readable case title
- `attack_family` (string): confidence_calibration | partial_sync_bleed | multi_hop_provenance_asymmetry
- `attack_subtype` (string): Specific attack variant
- `difficulty` (string): easy | medium | hard
- `control` (bool): true for control cases, false for attack cases
- `description` (string): 1-3 sentence description of the attack/control
- `world_state` (object): Objective facts the memory claims should be measured against
- `agents` (array): 2-5 agent definitions with id, role, trust_level, sync_state
- `memory_entries` (array): 3-20 MemCube-format entries
- `sync_topology` (object): For PS cases — sync graph, delay config, partition info
- `event_timeline` (array): 4-12 chronological events
- `query` (object): The action being evaluated — action_type, domain, intent
- `ground_truth` (object): Manually authored correct decision + reasoning
- `expected_system_behavior` (object): What Sgraal should do — allowed_decisions, must_detect
- `confidence_signal` (object): For CC cases — model_confidence, expected_confidence, calibration_label, confidence_delta
- `scoring_hooks` (object): Expected component scores and detection flags
- `metadata` (object): Generation info, tags, notes

## Case Matrix

See main task description for exact distribution of 60 cases across subtypes.

## Validation Checklist

Every valid record must have:
- case_id matching R12-{XX}-{NNN}
- attack_family in {confidence_calibration, partial_sync_bleed, multi_hop_provenance_asymmetry}
- At least 1 agent
- At least 1 memory_entry with id, content, type, timestamp_age_days, source_trust
- query with action_type and domain
- ground_truth.correct_decision in {USE_MEMORY, WARN, ASK_USER, BLOCK}
- expected_system_behavior.allowed_decisions (non-empty array)
- CC cases: confidence_signal present
- PS cases: sync_topology present + at least 1 partial_sync_delay event
- PA cases: at least 1 path with hop_count >= 3 + asymmetry_score + downstream_skew_score
