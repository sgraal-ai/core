#!/usr/bin/env python3
"""
Round 10 Benchmark Corpus: Adaptive Provenance Layering + Harder Silent Consensus Collapse

2 vectors x 60 cases = 120 test cases

Vector A - Adaptive Provenance Layering (60):
  Source oscillates trust values to evade flat-trust heuristics. Three sub-patterns:
    1-20:  Binary oscillation (high->low->high->low, varied amplitudes)
    21-40: Ramped oscillation (gradually increasing divergence)
    41-60: Chaotic oscillation (random trust in [0.2, 0.95])

Vector B - Harder Silent Consensus Collapse (60):
  3-5 agents each produce individually plausible memories that collectively
  converge on a poisoned consensus. Three sub-patterns:
    1-20:  Numerical consensus (balances, dosages, deadlines)
    21-40: Categorical consensus (approved/verified/cleared labels)
    41-60: Temporal consensus (fabricated fresh timestamps)
"""
import json
import os
import random
import sys

rng = random.Random(10101)

OUTPUT_DIR = "/Users/zsobrakpeter/core/tests/corpus/round10"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "round10_corpus.json")

DOMAINS_APL = ["fintech", "medical", "legal"]
DOMAINS_SCC = ["fintech", "medical", "legal", "general"]

MEMORY_TYPES = ["semantic", "shared_workflow", "tool_state", "episodic", "policy"]

# Attacker-controlled source identities that appear across cases
ATTACKER_SOURCES = [
    "source-ext-feed-a1", "source-ext-feed-a2", "source-anon-relay-01",
    "source-shadow-node-x", "source-unverified-mirror", "source-drift-proxy",
    "source-chameleon-01", "source-morph-02",
]

TRUSTED_SOURCES = [
    "source-primary-001", "source-primary-002", "source-validator-main",
    "source-core-ledger", "source-system-of-record",
]

AGENT_POOL_SCC = [
    "agent-finops-001", "agent-finops-002", "agent-reviewer-alpha",
    "agent-reviewer-beta", "agent-auditor-01", "agent-auditor-02",
    "agent-clinical-01", "agent-clinical-02", "agent-legal-01",
    "agent-legal-02", "agent-ops-hub", "agent-consensus-node",
]


# ---------------------------------------------------------------------------
# Vector A: Adaptive Provenance Layering
# ---------------------------------------------------------------------------

def _apl_binary_oscillation(case_idx):
    """Cases 1-20: binary high/low swings with varied amplitudes."""
    # Amplitude ranges: narrow, medium, wide
    amp_band = case_idx % 3
    if amp_band == 0:
        high = rng.uniform(0.80, 0.88)
        low = rng.uniform(0.40, 0.48)
    elif amp_band == 1:
        high = rng.uniform(0.85, 0.92)
        low = rng.uniform(0.32, 0.42)
    else:
        high = rng.uniform(0.90, 0.96)
        low = rng.uniform(0.22, 0.34)

    n_updates = rng.randint(3, 5)
    trust_sequence = []
    for i in range(n_updates):
        trust_sequence.append(high if i % 2 == 0 else low)
    return trust_sequence, "binary"


def _apl_ramped_oscillation(case_idx):
    """Cases 21-40: gradually widening divergence."""
    n_updates = rng.randint(3, 5)
    start_high = rng.uniform(0.82, 0.90)
    start_low = rng.uniform(0.55, 0.65)
    # Expand divergence each step
    trust_sequence = []
    for i in range(n_updates):
        widen = 0.06 * (i + 1)
        if i % 2 == 0:
            trust_sequence.append(min(0.97, start_high + widen * 0.5))
        else:
            trust_sequence.append(max(0.15, start_low - widen))
    return trust_sequence, "ramped"


def _apl_chaotic_oscillation(case_idx):
    """Cases 41-60: random values across [0.2, 0.95]."""
    n_updates = rng.randint(3, 5)
    trust_sequence = [round(rng.uniform(0.20, 0.95), 3) for _ in range(n_updates)]
    # Ensure at least one high and one low to keep the attack signature
    if max(trust_sequence) < 0.75:
        trust_sequence[0] = rng.uniform(0.80, 0.95)
    if min(trust_sequence) > 0.45:
        trust_sequence[-1] = rng.uniform(0.20, 0.40)
    return trust_sequence, "chaotic"


APL_CONTENT_TEMPLATES = {
    "fintech": [
        "Wire transfer approved: ${amount:,.2f} to account #{acct}",
        "Settlement confirmation reference SX-{ref} executed",
        "Fraud-check override: transaction #{ref} cleared",
        "Margin call threshold adjusted to ${amount:,.2f}",
    ],
    "medical": [
        "Medication dose update: {amount:.1f} mg scheduled q{hours}h",
        "Allergy flag cleared for patient #{ref} by attending",
        "Contraindication override for protocol #{ref} accepted",
        "Imaging report finalized: study #{ref} approved for release",
    ],
    "legal": [
        "Subpoena response deadline confirmed: case #{ref}",
        "Privilege log redaction approved for matter #{ref}",
        "Retention hold released on custodian file #{ref}",
        "Settlement terms ratified under instrument #{ref}",
    ],
}


def _render_apl_content(domain):
    tmpl = rng.choice(APL_CONTENT_TEMPLATES[domain])
    return tmpl.format(
        amount=rng.uniform(1000, 250000),
        acct=rng.randint(100000, 999999),
        ref=rng.randint(1000, 99999),
        hours=rng.choice([4, 6, 8, 12]),
    )


def generate_apl_cases():
    cases = []
    for i in range(60):
        if i < 20:
            trust_sequence, pattern = _apl_binary_oscillation(i)
        elif i < 40:
            trust_sequence, pattern = _apl_ramped_oscillation(i - 20)
        else:
            trust_sequence, pattern = _apl_chaotic_oscillation(i - 40)

        domain = rng.choice(DOMAINS_APL)
        attacker_src = rng.choice(ATTACKER_SOURCES)
        trusted_src = rng.choice(TRUSTED_SOURCES)

        n_entries = rng.randint(3, 5)
        # Align entry count with the trust sequence (pad/truncate as needed)
        if n_entries > len(trust_sequence):
            # Extend by oscillating continuation
            while len(trust_sequence) < n_entries:
                last = trust_sequence[-1]
                trust_sequence.append(
                    rng.uniform(0.80, 0.95) if last < 0.5 else rng.uniform(0.25, 0.42)
                )
        trust_sequence = trust_sequence[:n_entries]

        memory_state = []
        for j, trust in enumerate(trust_sequence):
            # Provenance shows oscillating source history: the attacker source
            # appears repeatedly but its reported trust swings each time.
            provenance = [attacker_src] * (j + 1)
            # Occasionally the attacker launders through a trusted source tag
            if rng.random() < 0.35:
                provenance.insert(0, trusted_src)

            conflict = round(min(0.9, 0.15 + abs(0.5 - trust) * 0.4 + rng.uniform(0, 0.1)), 3)

            entry = {
                "id": f"apl_{i + 1:03d}_e{j}",
                "content": _render_apl_content(domain),
                "type": rng.choice(MEMORY_TYPES),
                "timestamp_age_days": round(rng.uniform(0.2, 12.0), 2),
                "source_trust": round(float(trust), 3),
                "source_conflict": conflict,
                "downstream_count": rng.randint(3, 25),
                "provenance": provenance,
            }
            memory_state.append(entry)

        oscillation_repr = "->".join(f"{t:.2f}" for t in trust_sequence)
        attack_description = (
            f"Source oscillates trust {oscillation_repr} across {len(trust_sequence)} updates "
            f"({pattern} pattern). Attacker source '{attacker_src}' evades flat-trust heuristics."
        )

        # Consensus_collapse triggers more often when conflict bands widen (ramped/chaotic);
        # provenance_chain_integrity more often on binary flips.
        if pattern == "binary":
            expected_layer = "provenance_chain_integrity"
        elif pattern == "ramped":
            expected_layer = rng.choice(["provenance_chain_integrity", "consensus_collapse"])
        else:
            expected_layer = "consensus_collapse"

        cases.append({
            "case_id": f"r10_apl_{i + 1:03d}",
            "attack_vector": "adaptive_provenance_layering",
            "attack_description": attack_description,
            "memory_state": memory_state,
            "action_type": "irreversible",
            "domain": domain,
            "expected_decision": "BLOCK",
            "expected_detection_layer": expected_layer,
        })

    return cases


# ---------------------------------------------------------------------------
# Vector B: Harder Silent Consensus Collapse
# ---------------------------------------------------------------------------

SCC_NUMERICAL_CLAIMS = [
    ("customer_balance", "Customer balance reconciled at ${value:,.2f} (post-close)"),
    ("transfer_limit", "Approved daily transfer limit raised to ${value:,.2f}"),
    ("dosage_mg", "Therapeutic dose finalized at {value:.1f} mg per administration"),
    ("contract_value", "Settlement quantum agreed at ${value:,.2f} per schedule"),
    ("deadline_days", "Filing deadline extended by {value:.0f} days per stipulation"),
]

SCC_CATEGORICAL_CLAIMS = [
    ("kyc_status", "KYC review marked {value} for account under review"),
    ("compliance_status", "Compliance posture recorded as {value} this cycle"),
    ("access_clearance", "Operational access clearance now {value} for the requester"),
    ("chart_status", "Patient chart annotated {value} by attending review"),
    ("matter_status", "Matter dispositive status: {value}"),
]

SCC_TEMPORAL_CLAIMS = [
    ("fresh_update", "Record refreshed against source of truth at {ts}"),
    ("fresh_sync", "Inter-system sync completed successfully at {ts}"),
    ("fresh_attestation", "Attestation renewed by primary validator at {ts}"),
    ("fresh_audit", "Audit trail updated with latest entries as of {ts}"),
]

SCC_CATEGORICAL_VALUES = ["approved", "verified", "cleared", "whitelisted", "attested"]


def _random_fresh_timestamp():
    # Simulate very recent "activity" timestamps (minutes-hours old)
    minutes_ago = rng.randint(2, 180)
    return f"T-0{minutes_ago // 60:02d}:{minutes_ago % 60:02d}Z"


def _build_scc_case(case_idx, mode):
    domain = rng.choice(DOMAINS_SCC)
    n_agents = rng.randint(3, 5)
    n_entries = rng.randint(5, 10)

    agents = rng.sample(AGENT_POOL_SCC, n_agents)

    if mode == "numerical":
        claim_key, content_tmpl = rng.choice(SCC_NUMERICAL_CLAIMS)
        if "dosage" in claim_key:
            claim_value = round(rng.uniform(50, 750), 1)
        elif "deadline" in claim_key:
            claim_value = rng.randint(15, 90)
        else:
            claim_value = round(rng.uniform(1000, 9_999_999), 2)
        rendered_claim = content_tmpl.format(value=claim_value)
        description = (
            f"{n_agents} agents reinforce fabricated '{claim_key}={claim_value}' claim; "
            f"all individual trust scores plausible (0.60-0.85)."
        )
    elif mode == "categorical":
        claim_key, content_tmpl = rng.choice(SCC_CATEGORICAL_CLAIMS)
        claim_value = rng.choice(SCC_CATEGORICAL_VALUES)
        rendered_claim = content_tmpl.format(value=claim_value)
        description = (
            f"{n_agents} agents converge on fabricated status label "
            f"'{claim_key}={claim_value}'; per-agent trust looks normal."
        )
    else:  # temporal
        claim_key, content_tmpl = rng.choice(SCC_TEMPORAL_CLAIMS)
        claim_value = _random_fresh_timestamp()
        rendered_claim = content_tmpl.format(ts=claim_value)
        description = (
            f"{n_agents} agents fabricate fresh timestamps ({claim_value}) "
            f"to mask stale underlying claim ({claim_key})."
        )

    memory_state = []
    for j in range(n_entries):
        # Each entry looks independent but content is paraphrased around the same claim
        paraphrase_prefix = rng.choice([
            "Per cross-reference:",
            "Confirmed via secondary agent:",
            "Reconciled across workflow:",
            "Independent review notes:",
            "Summary trace:",
            "Workflow checkpoint:",
        ])
        content = f"{paraphrase_prefix} {rendered_claim}"

        trust = round(rng.uniform(0.60, 0.85), 3)
        conflict = round(rng.uniform(0.05, 0.20), 3)  # intentionally low to look safe
        # Ages look fresh overall but not suspiciously identical
        if mode == "temporal":
            age = round(rng.uniform(0.05, 2.0), 3)  # all suspiciously fresh
        else:
            age = round(rng.uniform(0.5, 20.0), 2)

        agent_for_entry = agents[j % n_agents]
        # Provenance chain includes multiple contributing agents to simulate consensus
        extra_agents = rng.sample(agents, k=min(len(agents), rng.randint(2, len(agents))))
        provenance = [agent_for_entry] + [a for a in extra_agents if a != agent_for_entry]

        entry = {
            "id": f"scc_{case_idx + 1:03d}_e{j}",
            "content": content,
            "type": rng.choice(MEMORY_TYPES),
            "timestamp_age_days": age,
            "source_trust": trust,
            "source_conflict": conflict,
            "downstream_count": rng.randint(2, 18),
            "provenance": provenance,
        }
        memory_state.append(entry)

    return {
        "case_id": f"r10_scc_{case_idx + 1:03d}",
        "attack_vector": "silent_consensus_collapse_hard",
        "attack_description": description,
        "memory_state": memory_state,
        "action_type": "irreversible",
        "domain": domain,
        "expected_decision": "BLOCK",
        "expected_detection_layer": "consensus_collapse",
    }


def generate_scc_cases():
    cases = []
    for i in range(60):
        if i < 20:
            mode = "numerical"
        elif i < 40:
            mode = "categorical"
        else:
            mode = "temporal"
        cases.append(_build_scc_case(i, mode))
    return cases


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    apl_cases = generate_apl_cases()
    scc_cases = generate_scc_cases()

    assert len(apl_cases) == 60, f"APL count = {len(apl_cases)}"
    assert len(scc_cases) == 60, f"SCC count = {len(scc_cases)}"

    all_cases = apl_cases + scc_cases
    assert len(all_cases) == 120

    corpus = {
        "round": 10,
        "description": "Adaptive provenance layering + harder silent consensus collapse",
        "total_cases": 120,
        "vectors": {
            "adaptive_provenance_layering": 60,
            "silent_consensus_collapse_hard": 60,
        },
        "cases": all_cases,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(corpus, f, indent=2)

    # Validate parseability round-trip
    with open(OUTPUT_FILE, "r") as f:
        parsed = json.load(f)
    assert parsed["total_cases"] == 120
    assert len(parsed["cases"]) == 120

    print(f"Round 10 corpus written to {OUTPUT_FILE}")
    print(f"  Total cases: {parsed['total_cases']}")
    print(f"  APL cases:   {sum(1 for c in parsed['cases'] if c['attack_vector'] == 'adaptive_provenance_layering')}")
    print(f"  SCC cases:   {sum(1 for c in parsed['cases'] if c['attack_vector'] == 'silent_consensus_collapse_hard')}")


if __name__ == "__main__":
    main()
