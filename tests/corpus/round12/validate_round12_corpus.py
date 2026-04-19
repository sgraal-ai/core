"""Structural validator for Round 12 corpus. Must pass 100% before Phase 2 calibration."""
import json
import os
import sys
import re

CORPUS_PATH = os.path.join(os.path.dirname(__file__), "round12_corpus.json")

VALID_FAMILIES = {"confidence_calibration", "partial_sync_bleed", "multi_hop_provenance_asymmetry"}
VALID_DECISIONS = {"USE_MEMORY", "WARN", "ASK_USER", "BLOCK"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_TRUTH_ALIGNMENTS = {"aligned", "misaligned", "partial"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}
VALID_CALIBRATION_LABELS = {"OVERCONFIDENT", "UNDERCONFIDENT", "CALIBRATED"}
CASE_ID_PATTERN = re.compile(r"^R12-(CC|PS|PA)-\d{3}$")

GROUND_TRUTH_REQUIRED = [
    "correct_decision", "memory_safe_to_act", "primary_failure_dimension",
    "secondary_failure_dimension", "truth_alignment", "attack_present",
    "attack_success_if_unchecked", "consensus_is_independent",
    "expected_calibration_label", "bleed_present", "asymmetry_present", "severity",
    "reasoning", "key_signals",
]


def validate():
    errors = []

    with open(CORPUS_PATH) as f:
        data = json.load(f)

    cases = data.get("cases", [])

    # --- Global checks ---
    if len(cases) != 60:
        errors.append(f"GLOBAL: expected 60 cases, got {len(cases)}")

    # Family counts
    family_counts = {}
    for c in cases:
        fam = c.get("attack_family", "MISSING")
        family_counts[fam] = family_counts.get(fam, 0) + 1
    for fam in VALID_FAMILIES:
        if family_counts.get(fam, 0) != 20:
            errors.append(f"GLOBAL: {fam} has {family_counts.get(fam, 0)} cases, expected 20")

    # Unique case IDs
    ids = [c.get("case_id", "") for c in cases]
    dupes = set(x for x in ids if ids.count(x) > 1)
    if dupes:
        errors.append(f"GLOBAL: duplicate case_ids: {dupes}")

    # --- Per-case checks ---
    for c in cases:
        cid = c.get("case_id", "UNKNOWN")
        prefix = f"{cid}:"

        # Case ID format
        if not CASE_ID_PATTERN.match(cid):
            errors.append(f"{prefix} case_id does not match R12-XX-NNN pattern")

        # Attack family
        fam = c.get("attack_family")
        if fam not in VALID_FAMILIES:
            errors.append(f"{prefix} invalid attack_family: {fam}")

        # Difficulty
        if c.get("difficulty") not in VALID_DIFFICULTIES:
            errors.append(f"{prefix} invalid difficulty: {c.get('difficulty')}")

        # Agents
        agents = c.get("agents", [])
        if len(agents) < 1:
            errors.append(f"{prefix} no agents")

        # Memory entries
        entries = c.get("memory_entries", [])
        if len(entries) < 1:
            errors.append(f"{prefix} no memory_entries")
        for i, e in enumerate(entries):
            for field in ["id", "content", "type", "timestamp_age_days", "source_trust"]:
                if field not in e:
                    errors.append(f"{prefix} memory_entry[{i}] missing {field}")

        # Event timeline
        events = c.get("event_timeline", [])
        if len(events) < 4:
            errors.append(f"{prefix} event_timeline has {len(events)} events, minimum 4")

        # Query
        query = c.get("query", {})
        if "action_type" not in query:
            errors.append(f"{prefix} query missing action_type")
        if "domain" not in query:
            errors.append(f"{prefix} query missing domain")

        # Ground truth (14 fields)
        gt = c.get("ground_truth", {})
        for field in GROUND_TRUTH_REQUIRED:
            if field not in gt:
                errors.append(f"{prefix} ground_truth missing {field}")
        if gt.get("correct_decision") not in VALID_DECISIONS:
            errors.append(f"{prefix} invalid correct_decision: {gt.get('correct_decision')}")
        if gt.get("truth_alignment") not in VALID_TRUTH_ALIGNMENTS:
            errors.append(f"{prefix} invalid truth_alignment: {gt.get('truth_alignment')}")
        if gt.get("severity") not in VALID_SEVERITIES:
            errors.append(f"{prefix} invalid severity: {gt.get('severity')}")

        # Expected system behavior
        esb = c.get("expected_system_behavior", {})
        if not esb.get("allowed_decisions"):
            errors.append(f"{prefix} expected_system_behavior.allowed_decisions empty or missing")

        # --- Vector-specific checks ---

        # CC: confidence_signal required
        if fam == "confidence_calibration":
            cs = c.get("confidence_signal")
            if not cs or not isinstance(cs, dict):
                errors.append(f"{prefix} CC case missing confidence_signal")
            elif "model_confidence" not in cs:
                errors.append(f"{prefix} CC confidence_signal missing model_confidence")
            elif "calibration_label" not in cs:
                errors.append(f"{prefix} CC confidence_signal missing calibration_label")

        # PS: sync_topology + partial_sync_delay event + version mismatch
        if fam == "partial_sync_bleed":
            st = c.get("sync_topology")
            if not st or not isinstance(st, dict):
                errors.append(f"{prefix} PS case missing sync_topology")
            # Check for partial_sync_delay event
            has_delay = any("partial_sync_delay" in str(ev.get("event", "")).lower() or
                           "sync_delay" in str(ev.get("event", "")).lower() or
                           "partial_sync" in str(ev.get("event", "")).lower() or
                           "delay" in str(ev.get("detail", "")).lower()
                           for ev in events)
            if not has_delay:
                errors.append(f"{prefix} PS case has no partial_sync_delay-related event")
            # Check for version mismatch
            versions = set()
            for a in agents:
                v = a.get("memory_view_version")
                if v:
                    versions.add(v)
            if len(versions) < 2:
                errors.append(f"{prefix} PS case needs ≥2 different memory_view_versions, got {versions}")

        # PA: path with hop_count >= 3 + asymmetry fields + source origins
        if fam == "multi_hop_provenance_asymmetry":
            has_valid_path = False
            for e in entries:
                p = e.get("path")
                if p and isinstance(p, dict) and p.get("hop_count", 0) >= 3:
                    has_valid_path = True
                    if "asymmetry_score" not in p:
                        errors.append(f"{prefix} path missing asymmetry_score in {e.get('id')}")
                    if "downstream_skew_score" not in p:
                        errors.append(f"{prefix} path missing downstream_skew_score in {e.get('id')}")
                src = e.get("source")
                if src and isinstance(src, dict):
                    if "declared_origin" not in src:
                        errors.append(f"{prefix} source missing declared_origin in {e.get('id')}")
                    if "actual_origin" not in src:
                        errors.append(f"{prefix} source missing actual_origin in {e.get('id')}")
            if not has_valid_path:
                errors.append(f"{prefix} PA case has no path with hop_count >= 3")

    return errors


def main():
    errors = validate()
    if errors:
        print(f"VALIDATION FAILED: {len(errors)} errors\n")
        for e in errors:
            print(f"  ERROR: {e}")
        sys.exit(1)
    else:
        print("VALIDATION PASSED: all 60 cases valid")
        sys.exit(0)


if __name__ == "__main__":
    main()


# pytest integration
def test_round12_corpus_valid():
    errors = validate()
    assert not errors, f"Round 12 corpus validation failed with {len(errors)} errors:\n" + "\n".join(errors[:20])
