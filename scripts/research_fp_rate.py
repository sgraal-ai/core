#!/usr/bin/env python3
"""
Research Task #445: False positive rate measurement for detection layers.

Generates 200 benign memory states that could plausibly trigger each detection
layer, runs them through preflight, and measures false positive rates.
"""
import sys, os, json, random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test env before importing app
os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
os.environ["SGRAAL_TEST_MODE"] = "1"

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}


def _entry(**overrides):
    defaults = {
        "id": "benign_001", "content": "Benign test memory", "type": "semantic",
        "timestamp_age_days": 5, "source_trust": 0.85, "source_conflict": 0.1,
        "downstream_count": 3,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Category 1: Legitimate timestamp patterns (should NOT trigger timestamp_integrity)
# ---------------------------------------------------------------------------
def generate_timestamp_benign(n=50):
    """Entries with legitimate age patterns that could look suspicious:
    - Very fresh entries (age ~0) — legitimate real-time data
    - Entries with round ages (7, 14, 30 days) — scheduled updates
    - Entries with very old but stable data (identity, policy)
    - Entries with clustered ages — batch imports
    """
    rng = random.Random(42)
    entries_list = []
    for i in range(n):
        variant = i % 5
        if variant == 0:
            # Very fresh — real-time tool state
            e = [_entry(id=f"ts_fresh_{i}", content=f"Live API response at {rng.randint(1,12)}:{rng.randint(0,59):02d}",
                        type="tool_state", timestamp_age_days=round(rng.uniform(0.001, 0.1), 3),
                        source_trust=0.9, source_conflict=0.05, downstream_count=rng.randint(1, 5))]
        elif variant == 1:
            # Round ages — scheduled weekly/monthly updates
            age = rng.choice([7, 14, 21, 28, 30, 60, 90])
            e = [_entry(id=f"ts_round_{i}", content=f"Monthly report from department {rng.choice(['sales','eng','ops'])}",
                        type="semantic", timestamp_age_days=age,
                        source_trust=0.85, source_conflict=0.1, downstream_count=rng.randint(2, 8))]
        elif variant == 2:
            # Very old identity/policy — legitimately ancient
            e = [_entry(id=f"ts_old_{i}", content=f"Company policy established in founding year",
                        type="identity", timestamp_age_days=rng.randint(300, 800),
                        source_trust=0.95, source_conflict=0.02, downstream_count=rng.randint(1, 3))]
        elif variant == 3:
            # Batch import — multiple entries with nearly identical ages
            base_age = rng.uniform(1, 10)
            e = [_entry(id=f"ts_batch_{i}_a", content=f"Batch imported record A from CRM sync",
                        type="shared_workflow", timestamp_age_days=round(base_age, 2),
                        source_trust=0.8, source_conflict=0.1, downstream_count=2),
                 _entry(id=f"ts_batch_{i}_b", content=f"Batch imported record B from CRM sync",
                        type="shared_workflow", timestamp_age_days=round(base_age + rng.uniform(0, 0.01), 2),
                        source_trust=0.8, source_conflict=0.1, downstream_count=2)]
        else:
            # Mixed ages — diverse but legitimate
            e = [_entry(id=f"ts_mixed_{i}", content=f"Knowledge base article version {rng.randint(1,20)}",
                        type="semantic", timestamp_age_days=round(rng.uniform(0.5, 200), 1),
                        source_trust=rng.uniform(0.7, 0.95), source_conflict=rng.uniform(0.02, 0.15),
                        downstream_count=rng.randint(1, 10))]
        entries_list.append(e)
    return entries_list


# ---------------------------------------------------------------------------
# Category 2: Legitimate multi-source agreement (should NOT trigger consensus_collapse)
# ---------------------------------------------------------------------------
def generate_consensus_benign(n=50):
    """Multiple sources genuinely agreeing:
    - Different trust levels but same general information
    - Independent sources confirming a fact
    - Corroborating observations from different agents
    """
    rng = random.Random(43)
    entries_list = []
    for i in range(n):
        variant = i % 4
        if variant == 0:
            # Two independent sources, moderate trust, low conflict
            e = [_entry(id=f"con_indep_{i}_a", content=f"Product price is ${rng.randint(10,500)}.{rng.randint(0,99):02d}",
                        type="semantic", timestamp_age_days=rng.uniform(1, 5),
                        source_trust=rng.uniform(0.7, 0.9), source_conflict=rng.uniform(0.05, 0.15), downstream_count=3),
                 _entry(id=f"con_indep_{i}_b", content=f"Product price confirmed at ${rng.randint(10,500)}.{rng.randint(0,99):02d}",
                        type="semantic", timestamp_age_days=rng.uniform(1, 5),
                        source_trust=rng.uniform(0.7, 0.9), source_conflict=rng.uniform(0.05, 0.15), downstream_count=2)]
        elif variant == 1:
            # Three sources with varying trust
            e = [_entry(id=f"con_three_{i}_{j}", content=f"Server status: healthy (check {j})",
                        type="tool_state", timestamp_age_days=rng.uniform(0.1, 1),
                        source_trust=rng.uniform(0.6, 0.95), source_conflict=rng.uniform(0.03, 0.1),
                        downstream_count=rng.randint(1, 4))
                 for j in range(3)]
        elif variant == 2:
            # High-trust single authoritative source
            e = [_entry(id=f"con_auth_{i}", content=f"Official regulation {rng.randint(100,999)}.{rng.randint(1,50)}",
                        type="policy", timestamp_age_days=rng.uniform(10, 100),
                        source_trust=0.95, source_conflict=0.03, downstream_count=rng.randint(5, 15))]
        else:
            # Preference + observation agreeing
            e = [_entry(id=f"con_pref_{i}", content=f"User prefers dark mode and compact layout",
                        type="preference", timestamp_age_days=rng.uniform(1, 30),
                        source_trust=0.9, source_conflict=0.05, downstream_count=1),
                 _entry(id=f"con_obs_{i}", content=f"UI rendered in dark theme based on settings",
                        type="episodic", timestamp_age_days=rng.uniform(0.1, 2),
                        source_trust=0.85, source_conflict=0.08, downstream_count=1)]
        entries_list.append(e)
    return entries_list


# ---------------------------------------------------------------------------
# Category 3: Legitimate identity delegation (should NOT trigger identity_drift)
# ---------------------------------------------------------------------------
def generate_identity_benign(n=50):
    """Legitimate authority patterns:
    - Admin delegating to team member
    - System-to-system trust chains
    - Normal organizational hierarchy
    """
    rng = random.Random(44)
    entries_list = []
    roles = ["admin", "manager", "analyst", "engineer", "reviewer"]
    for i in range(n):
        variant = i % 4
        if variant == 0:
            # Normal role description
            role = rng.choice(roles)
            e = [_entry(id=f"id_role_{i}", content=f"Agent operates as {role} with standard permissions",
                        type="identity", timestamp_age_days=rng.uniform(1, 100),
                        source_trust=0.9, source_conflict=0.05, downstream_count=rng.randint(1, 5))]
        elif variant == 1:
            # Team context
            e = [_entry(id=f"id_team_{i}", content=f"Member of engineering team, reports to lead",
                        type="identity", timestamp_age_days=rng.uniform(10, 200),
                        source_trust=0.85, source_conflict=0.08, downstream_count=2),
                 _entry(id=f"id_task_{i}", content=f"Currently assigned to code review task",
                        type="episodic", timestamp_age_days=rng.uniform(0.5, 5),
                        source_trust=0.8, source_conflict=0.1, downstream_count=3)]
        elif variant == 2:
            # System integration context
            e = [_entry(id=f"id_sys_{i}", content=f"Connected via OAuth2 with read-only scope",
                        type="tool_state", timestamp_age_days=rng.uniform(0.1, 10),
                        source_trust=0.92, source_conflict=0.04, downstream_count=rng.randint(1, 6))]
        else:
            # Normal provenance chain (2 hops)
            e = [_entry(id=f"id_chain_{i}", content=f"Data verified by quality assurance pipeline",
                        type="shared_workflow", timestamp_age_days=rng.uniform(1, 20),
                        source_trust=rng.uniform(0.75, 0.9), source_conflict=rng.uniform(0.05, 0.12),
                        downstream_count=rng.randint(2, 8),
                        provenance_chain=[f"source_{rng.randint(1,10)}", f"validator_{rng.randint(1,5)}"])]
        entries_list.append(e)
    return entries_list


# ---------------------------------------------------------------------------
# Category 4: Normal provenance chains (should NOT trigger provenance_chain_integrity)
# ---------------------------------------------------------------------------
def generate_provenance_benign(n=50):
    """Normal multi-hop provenance:
    - Short chains (1-2 hops)
    - Chains with diverse agent names
    - Chains where trust decreases slightly per hop (natural)
    """
    rng = random.Random(45)
    entries_list = []
    agent_pools = [f"agent_{c}_{rng.randint(1,99)}" for c in ["data", "process", "validate", "enrich", "serve"]]
    for i in range(n):
        variant = i % 4
        chain_len = rng.choice([1, 2, 2, 3]) if variant < 3 else 1
        chain = [rng.choice(agent_pools) for _ in range(chain_len)]
        # Ensure unique agents in chain
        chain = list(dict.fromkeys(chain))[:chain_len]
        trust = 0.95 - 0.03 * len(chain)  # Slight trust decay per hop
        if variant == 0:
            e = [_entry(id=f"prov_short_{i}", content=f"Customer feedback processed through {len(chain)} stages",
                        type="episodic", timestamp_age_days=rng.uniform(1, 15),
                        source_trust=round(trust, 2), source_conflict=rng.uniform(0.03, 0.1),
                        downstream_count=rng.randint(1, 5), provenance_chain=chain)]
        elif variant == 1:
            e = [_entry(id=f"prov_diverse_{i}", content=f"Market data aggregated from {len(chain)} feeds",
                        type="semantic", timestamp_age_days=rng.uniform(0.5, 7),
                        source_trust=round(trust, 2), source_conflict=rng.uniform(0.05, 0.12),
                        downstream_count=rng.randint(2, 10), provenance_chain=chain)]
        elif variant == 2:
            e = [_entry(id=f"prov_verified_{i}", content=f"Document reviewed and approved by compliance",
                        type="policy", timestamp_age_days=rng.uniform(5, 60),
                        source_trust=round(trust + 0.02, 2), source_conflict=0.05,
                        downstream_count=rng.randint(3, 12), provenance_chain=chain)]
        else:
            # Single source, no chain
            e = [_entry(id=f"prov_single_{i}", content=f"Direct observation by primary agent",
                        type="episodic", timestamp_age_days=rng.uniform(0.1, 3),
                        source_trust=0.92, source_conflict=0.04, downstream_count=rng.randint(1, 4))]
        entries_list.append(e)
    return entries_list


# ---------------------------------------------------------------------------
# Run all through preflight
# ---------------------------------------------------------------------------
def run_category(name, layer_field, entries_list):
    fp_count = 0
    total = len(entries_list)
    details = []

    for i, memory_state in enumerate(entries_list):
        r = client.post("/v1/preflight", headers=AUTH, json={
            "memory_state": memory_state,
            "action_type": "reversible",
            "domain": "general",
            "response_profile": "full",
        })
        if r.status_code != 200:
            details.append({"index": i, "error": r.status_code})
            continue

        j = r.json()
        layer_value = j.get(layer_field, "VALID")
        if isinstance(layer_value, str) and layer_value == "MANIPULATED":
            fp_count += 1
            details.append({
                "index": i,
                "layer_value": layer_value,
                "omega": j.get("omega_mem_final"),
                "action": j.get("recommended_action"),
                "entries": [e.get("id") for e in memory_state],
            })

    fp_rate = fp_count / max(total, 1)
    return {
        "layer": layer_field,
        "category": name,
        "fp_rate": round(fp_rate, 4),
        "fp_count": fp_count,
        "total": total,
        "target_met": fp_rate < 0.005,
        "false_positives": details if details else [],
    }


def main():
    print("=" * 60)
    print("  Research Task #445: False Positive Rate Measurement")
    print("=" * 60)
    print()

    categories = [
        ("Legitimate timestamps", "timestamp_integrity", generate_timestamp_benign()),
        ("Legitimate consensus", "consensus_collapse", generate_consensus_benign()),
        ("Legitimate identity", "identity_drift", generate_identity_benign()),
        ("Legitimate provenance", "provenance_chain_integrity", generate_provenance_benign()),
    ]

    results = []
    for name, layer, entries_list in categories:
        print(f"Running {name} ({len(entries_list)} cases)...")
        result = run_category(name, layer, entries_list)
        results.append(result)
        status = "PASS" if result["target_met"] else "FAIL"
        print(f"  {layer}: {result['fp_count']}/{result['total']} false positives "
              f"({result['fp_rate']*100:.1f}%) [{status}]")
        if result["false_positives"]:
            for fp in result["false_positives"][:3]:
                print(f"    FP: index={fp.get('index')} omega={fp.get('omega')} action={fp.get('action')}")
        print()

    # Summary
    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    total_fp = sum(r["fp_count"] for r in results)
    total_cases = sum(r["total"] for r in results)
    overall_rate = total_fp / max(total_cases, 1)
    for r in results:
        status = "PASS" if r["target_met"] else "FAIL"
        print(f"  {r['layer']:30s}  {r['fp_rate']*100:5.1f}%  ({r['fp_count']}/{r['total']})  [{status}]")
    print(f"  {'OVERALL':30s}  {overall_rate*100:5.1f}%  ({total_fp}/{total_cases})")
    print()
    all_pass = all(r["target_met"] for r in results)
    print(f"  All layers < 0.5%: {'YES' if all_pass else 'NO'}")
    print()

    with open("/tmp/fp_rate_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("  Detailed results: /tmp/fp_rate_results.json")


if __name__ == "__main__":
    main()
