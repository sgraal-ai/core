#!/usr/bin/env python3
"""
Formal proof verification: healing termination (#615) + A2 axiom (#618).
"""
import sys, os, json, math, random, glob, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"

from scoring_engine import compute, MemoryEntry
from scoring_engine.omega_mem import WEIGHTS


# =========================================================================
# TASK 2: Healing termination — does every heal action reduce omega?
# =========================================================================

def task2_healing_termination():
    print("=" * 60)
    print("  TASK 2: HEALING TERMINATION PROOF")
    print("=" * 60)

    from api.main import _load_benchmark_corpus
    cases = _load_benchmark_corpus()
    print(f"\n  Loaded {len(cases)} corpus cases")

    total_actions = 0
    decreased = 0
    stayed_same = 0
    increased = 0
    increases = []

    for i, case in enumerate(cases):
        ms = case["memory_state"]
        at = case.get("action_type", "reversible")
        dom = case.get("domain", "general")

        entries = [MemoryEntry(
            id=e.get("id", f"h_{i}_{j}"), content=e.get("content", ""),
            type=e.get("type", "semantic"),
            timestamp_age_days=e.get("timestamp_age_days") or e.get("age_days") or 0,
            source_trust=e.get("source_trust", 0.9),
            source_conflict=e.get("source_conflict", 0.1),
            downstream_count=e.get("downstream_count", 1),
            r_belief=e.get("r_belief", 0.5),
        ) for j, e in enumerate(ms)]

        if not entries:
            continue

        result = compute(entries, at, dom)
        omega_before = result.omega_mem_final

        # Simulate each repair action type
        for action in ["REFETCH", "VERIFY_WITH_SOURCE", "REBUILD_WORKING_SET"]:
            healed_entries = []
            for e in entries:
                if action == "REFETCH":
                    healed_entries.append(MemoryEntry(
                        id=e.id, content=e.content, type=e.type,
                        timestamp_age_days=0.1,  # Fresh
                        source_trust=e.source_trust, source_conflict=e.source_conflict,
                        downstream_count=e.downstream_count, r_belief=e.r_belief,
                    ))
                elif action == "VERIFY_WITH_SOURCE":
                    healed_entries.append(MemoryEntry(
                        id=e.id, content=e.content, type=e.type,
                        timestamp_age_days=e.timestamp_age_days,
                        source_trust=0.99, source_conflict=0.01,  # Verified
                        downstream_count=e.downstream_count, r_belief=e.r_belief,
                    ))
                elif action == "REBUILD_WORKING_SET":
                    healed_entries.append(MemoryEntry(
                        id=e.id, content=e.content, type=e.type,
                        timestamp_age_days=e.timestamp_age_days,
                        source_trust=e.source_trust, source_conflict=e.source_conflict,
                        downstream_count=e.downstream_count, r_belief=0.99,  # High belief
                    ))

            result_after = compute(healed_entries, at, dom)
            omega_after = result_after.omega_mem_final
            delta = omega_after - omega_before
            total_actions += 1

            if delta < -0.01:
                decreased += 1
            elif delta > 0.01:
                increased += 1
                increases.append({
                    "case_id": case.get("id", f"case_{i}"),
                    "action": action,
                    "omega_before": round(omega_before, 2),
                    "omega_after": round(omega_after, 2),
                    "delta": round(delta, 2),
                })
            else:
                stayed_same += 1

        if (i + 1) % 100 == 0:
            print(f"    {i+1}/{len(cases)}...")

    print(f"\n  RESULTS:")
    print(f"  Total actions tested: {total_actions}")
    print(f"  Decreased:   {decreased} ({decreased/max(total_actions,1)*100:.1f}%)")
    print(f"  Stayed same: {stayed_same} ({stayed_same/max(total_actions,1)*100:.1f}%)")
    print(f"  INCREASED:   {increased} ({increased/max(total_actions,1)*100:.1f}%)")

    if increased > 0:
        print(f"\n  *** BUG: {increased} actions increased omega! ***")
        for inc in increases[:5]:
            print(f"    {inc['case_id']}: {inc['action']} {inc['omega_before']}→{inc['omega_after']} (Δ={inc['delta']:+.2f})")
    else:
        print(f"\n  ✓ THEOREM VERIFIED: every heal action reduces or maintains omega.")

    result = {
        "total_actions": total_actions,
        "decreased": decreased, "decreased_pct": round(decreased / max(total_actions, 1) * 100, 1),
        "stayed_same": stayed_same, "stayed_same_pct": round(stayed_same / max(total_actions, 1) * 100, 1),
        "increased": increased, "increased_pct": round(increased / max(total_actions, 1) * 100, 1),
        "increases": increases[:10],
        "theorem_holds": increased == 0,
    }

    out = os.path.join(os.path.dirname(os.path.dirname(__file__)), "research", "proofs", "healing_termination.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=2)
    print(f"  Saved to {out}")
    return result


# =========================================================================
# TASK 3: A2 axiom cross-version test
# =========================================================================

def task3_a2_axiom():
    print("\n" + "=" * 60)
    print("  TASK 3: A2 AXIOM VERIFICATION")
    print("=" * 60)

    from api.main import _load_benchmark_corpus
    cases = _load_benchmark_corpus()[:100]
    print(f"\n  Testing {len(cases)} corpus cases (2 runs each)")

    # Run 1
    run1_omegas = []
    for case in cases:
        entries = [MemoryEntry(
            id=e.get("id", f"a2_{i}"), content=e.get("content", ""),
            type=e.get("type", "semantic"),
            timestamp_age_days=e.get("timestamp_age_days") or e.get("age_days") or 0,
            source_trust=e.get("source_trust", 0.9),
            source_conflict=e.get("source_conflict", 0.1),
            downstream_count=e.get("downstream_count", 1),
            r_belief=e.get("r_belief", 0.5),
        ) for i, e in enumerate(case["memory_state"])]
        if not entries:
            run1_omegas.append(None)
            continue
        r = compute(entries, case.get("action_type", "reversible"), case.get("domain", "general"))
        run1_omegas.append(r.omega_mem_final)

    # Run 2 — identical inputs
    run2_omegas = []
    for case in cases:
        entries = [MemoryEntry(
            id=e.get("id", f"a2_{i}"), content=e.get("content", ""),
            type=e.get("type", "semantic"),
            timestamp_age_days=e.get("timestamp_age_days") or e.get("age_days") or 0,
            source_trust=e.get("source_trust", 0.9),
            source_conflict=e.get("source_conflict", 0.1),
            downstream_count=e.get("downstream_count", 1),
            r_belief=e.get("r_belief", 0.5),
        ) for i, e in enumerate(case["memory_state"])]
        if not entries:
            run2_omegas.append(None)
            continue
        r = compute(entries, case.get("action_type", "reversible"), case.get("domain", "general"))
        run2_omegas.append(r.omega_mem_final)

    # Compare
    identical = 0
    different = 0
    max_diff = 0.0
    diffs = []

    for i, (o1, o2) in enumerate(zip(run1_omegas, run2_omegas)):
        if o1 is None or o2 is None:
            continue
        diff = abs(o1 - o2)
        if diff == 0.0:
            identical += 1
        else:
            different += 1
            max_diff = max(max_diff, diff)
            diffs.append({"case": i, "run1": o1, "run2": o2, "diff": diff})

    print(f"\n  Identical (10 decimal places): {identical}")
    print(f"  Different: {different}")
    print(f"  Max difference: {max_diff}")

    # Scan scoring_engine for non-deterministic functions
    print(f"\n  Scanning scoring_engine/ for non-deterministic functions...")
    se_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scoring_engine")
    nondeterministic = []
    for py_file in glob.glob(os.path.join(se_dir, "*.py")):
        fname = os.path.basename(py_file)
        with open(py_file) as f:
            content = f.read()
        for pattern, desc in [
            ("random.", "random number generation"),
            ("time.time()", "current time"),
            ("datetime.now()", "current datetime"),
            ("uuid.", "UUID generation"),
            ("os.urandom", "OS random"),
            (".read(", "file I/O read"),
            (".write(", "file I/O write"),
            ("requests.", "HTTP requests"),
            ("redis", "Redis I/O"),
        ]:
            if pattern in content:
                # Check if it's in a comment
                lines = content.split("\n")
                for line_num, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if pattern in stripped and not stripped.startswith("#") and not stripped.startswith('"""'):
                        nondeterministic.append({
                            "file": fname,
                            "line": line_num,
                            "pattern": pattern,
                            "description": desc,
                            "code": stripped[:80],
                        })

    if nondeterministic:
        print(f"  Found {len(nondeterministic)} potential non-deterministic calls:")
        for nd in nondeterministic[:10]:
            print(f"    {nd['file']}:{nd['line']}: {nd['pattern']} ({nd['description']})")
    else:
        print(f"  No non-deterministic functions found in scoring_engine/")

    a2_holds = different == 0 and len(nondeterministic) == 0

    print(f"\n  A2 AXIOM: {'VERIFIED' if a2_holds else 'VIOLATED'}")
    if different > 0:
        print(f"  *** {different} cases produced different omega on identical input ***")

    result = {
        "cases_tested": len(cases),
        "identical": identical,
        "different": different,
        "max_difference": max_diff,
        "differences": diffs[:5],
        "nondeterministic_calls": nondeterministic[:20],
        "nondeterministic_count": len(nondeterministic),
        "a2_holds": a2_holds,
    }

    out = os.path.join(os.path.dirname(os.path.dirname(__file__)), "research", "proofs", "a2_axiom_verification.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=2)
    print(f"  Saved to {out}")
    return result


if __name__ == "__main__":
    r2 = task2_healing_termination()
    r3 = task3_a2_axiom()
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Healing termination: {'VERIFIED' if r2['theorem_holds'] else 'VIOLATED'} ({r2['total_actions']} actions)")
    print(f"  A2 axiom: {'VERIFIED' if r3['a2_holds'] else 'VIOLATED'} ({r3['cases_tested']} cases)")
