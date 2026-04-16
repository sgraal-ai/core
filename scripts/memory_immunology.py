#!/usr/bin/env python3
"""
TASK 6 — Memory Immunology

Do attack patterns mutate across corpus rounds the way viruses mutate across
seasons?  We treat each BLOCK-ed case in a round as a sample attack,
extract a 10-component signature vector from its `/v1/preflight` response,
average per round, and measure cosine similarity between round centroids.

Method:
  1. Load R1-R4 + R9 cases via _load_benchmark_corpus()
     Load R5, R6, R7, R8 by parsing their corpus runner files
     Load R10 from tests/corpus/round10/round10_corpus.json
     Load R11 from tests/corpus/round11/round11_corpus.json
  2. For each case expected to BLOCK (or resulting in BLOCK), run preflight
     (dry_run=True) and grab the 10-component breakdown
  3. Mean signature per round = centroid
  4. Cosine similarity:
       consecutive pairs (R1->R2, R2->R3, ...)
       full NxN similarity matrix
  5. Phylogenetic tree: nearest-neighbour attach each subsequent centroid to
     the already-attached centroid with the highest cosine similarity.
     Edge length = 1 - cosine_similarity.
  6. Mutation rate:
       λ_mutation = (# consecutive pairs with cosine < 0.8) / (# pairs)
  7. Major clades: hierarchical single-link clustering at threshold
     cosine >= 0.9 groups rounds into clades.
"""
import ast
import glob
import json
import math
import os
import sys

os.environ["SGRAAL_SKIP_DNS_CHECK"] = "1"
sys.path.insert(0, "/Users/zsobrakpeter/core")

import numpy as np
from fastapi.testclient import TestClient
from api.main import app, _load_benchmark_corpus

client = TestClient(app)
AUTH = {"Authorization": "Bearer sg_test_key_001"}

OUT_JSON = "/Users/zsobrakpeter/core/research/results/memory_immunology.json"
OUT_MD = "/Users/zsobrakpeter/core/research/results/memory_immunology_section.md"

# Canonical 10-component order (taken from Sgraal scoring engine)
COMPONENT_ORDER = [
    "s_freshness", "s_drift", "s_provenance", "s_propagation", "s_recall",
    "r_encode", "s_interference", "s_recovery", "r_belief", "s_relevance",
]


# ---------------------------------------------------------------------------
# Corpus loaders
# ---------------------------------------------------------------------------

def _parse_py_cases(path, names):
    """Parse a Python runner file and return cases from the named literal lists."""
    src = open(path).read()
    mod = ast.parse(src)
    out = []
    for node in ast.walk(mod):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if (
                    isinstance(t, ast.Name)
                    and t.id in names
                    and isinstance(node.value, (ast.List, ast.Tuple))
                ):
                    try:
                        vals = ast.literal_eval(node.value)
                    except Exception:
                        continue
                    if isinstance(vals, list):
                        out.extend([v for v in vals if isinstance(v, dict)])
    return out


def load_round_cases():
    """Return {round_number: [case_dict, ...]}."""
    rounds = {k: [] for k in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]}

    # R1-R4 + R9 via the shared loader
    for c in _load_benchmark_corpus():
        r = c.get("round")
        if r in rounds:
            rounds[r].append({
                "memory_state": c.get("memory_state", []),
                "expected_decision": c.get("expected_decision", "USE_MEMORY"),
                "domain": c.get("domain", "general"),
                "action_type": c.get("action_type", "reversible"),
            })

    # R5
    r5 = _parse_py_cases(
        "/Users/zsobrakpeter/core/tests/corpus/round5_consensus_poisoning.py",
        names={"CASES"},
    )
    for c in r5:
        rounds[5].append({
            "memory_state": c.get("memory_state", []),
            "expected_decision": c.get("expected_decision", "BLOCK"),
            "domain": c.get("domain", "general"),
            "action_type": c.get("action_type", "reversible"),
        })

    # R6
    r6 = _parse_py_cases(
        "/Users/zsobrakpeter/core/tests/corpus/round6_memory_time_attack.py",
        names={"TIMESTAMP_ZEROING", "AGE_COLLAPSE", "ANCHOR_INCONSISTENCY"},
    )
    for c in r6:
        rounds[6].append({
            "memory_state": c.get("memory_state", []),
            "expected_decision": c.get("expected_decision", "BLOCK"),
            "domain": c.get("domain", "general"),
            "action_type": c.get("action_type", "reversible"),
        })

    # R7
    r7 = _parse_py_cases(
        "/Users/zsobrakpeter/core/tests/corpus/round7_identity_drift.py",
        names={"FAMILY_A", "FAMILY_B", "FAMILY_C", "FAMILY_D", "CLEAN_CASES"},
    )
    for c in r7:
        rounds[7].append({
            "memory_state": c.get("memory_state", []),
            "expected_decision": c.get("expected_decision", "BLOCK"),
            "domain": c.get("domain", "general"),
            "action_type": c.get("action_type", "reversible"),
        })

    # R8
    r8 = _parse_py_cases(
        "/Users/zsobrakpeter/core/tests/corpus/round8_consensus_collapse.py",
        names={"CASES"},
    )
    for c in r8:
        rounds[8].append({
            "memory_state": c.get("memory_state", []),
            "expected_decision": c.get("expected_decision", "BLOCK"),
            "domain": c.get("domain", "general"),
            "action_type": c.get("action_type", "reversible"),
        })

    # R10
    p10 = "/Users/zsobrakpeter/core/tests/corpus/round10/round10_corpus.json"
    if os.path.exists(p10):
        d = json.load(open(p10))
        for c in d.get("cases", []):
            rounds[10].append({
                "memory_state": c.get("memory_state", []),
                "expected_decision": c.get("expected_decision", "BLOCK"),
                "domain": c.get("domain", "general"),
                "action_type": c.get("action_type", "irreversible"),
            })

    # R11
    p11 = "/Users/zsobrakpeter/core/tests/corpus/round11/round11_corpus.json"
    if os.path.exists(p11):
        d = json.load(open(p11))
        for c in d.get("cases", []):
            rounds[11].append({
                "memory_state": c.get("memory_state", []),
                "expected_decision": c.get("expected_decision", "BLOCK"),
                "domain": c.get("domain", "general"),
                "action_type": c.get("action_type", "irreversible"),
            })

    return rounds


# ---------------------------------------------------------------------------
# Preflight signature extraction
# ---------------------------------------------------------------------------

def extract_signature(resp):
    """Return a 10-component float vector in canonical order, or None."""
    if not resp:
        return None
    comp = resp.get("component_breakdown") or {}
    if not comp:
        return None
    vec = []
    for key in COMPONENT_ORDER:
        v = comp.get(key)
        if v is None:
            # Some shipping responses use raw_score/final — take whichever exists
            # Otherwise zero-fill.
            v = 0.0
        # Breakdown entries may be dicts {raw:..., weighted:...}
        if isinstance(v, dict):
            v = v.get("raw") or v.get("weighted") or v.get("final") or v.get("value") or 0.0
        try:
            vec.append(float(v))
        except Exception:
            vec.append(0.0)
    return vec


def run_case(case):
    payload = {
        "memory_state": case.get("memory_state", []),
        "action_type": case.get("action_type", "reversible"),
        "domain": case.get("domain", "general"),
        "dry_run": True,
    }
    try:
        r = client.post("/v1/preflight", headers=AUTH, json=payload, timeout=30)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------

def cosine(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def build_phylo_tree(round_ids, centroids):
    """
    Root = first round. Subsequent rounds attach to the already-attached round
    with the maximum cosine similarity (nearest-neighbour stitching).
    Returns nested dict + parent-edge list.
    """
    if not round_ids:
        return {}, []

    parents = {round_ids[0]: None}
    edges = []
    attached = [round_ids[0]]

    for r in round_ids[1:]:
        best = None
        best_sim = -1.0
        for a in attached:
            s = cosine(centroids[r], centroids[a])
            if s > best_sim:
                best_sim = s
                best = a
        parents[r] = best
        edges.append({
            "child": r,
            "parent": best,
            "cosine_similarity": best_sim,
            "edge_length": round(1.0 - best_sim, 6),
        })
        attached.append(r)

    # Build nested structure
    children_map = {r: [] for r in round_ids}
    for r in round_ids[1:]:
        children_map[parents[r]].append(r)

    def _build_node(r):
        node = {"round": r, "children": []}
        for ch in children_map[r]:
            child_node = _build_node(ch)
            sim = cosine(centroids[r], centroids[ch])
            child_node["edge_length"] = round(1.0 - sim, 6)
            child_node["cosine_similarity"] = round(sim, 6)
            node["children"].append(child_node)
        return node

    tree = _build_node(round_ids[0])

    # ASCII rendering
    ascii_lines = []

    def _render(node, prefix="", is_last=True):
        conn = "└── " if is_last else "├── "
        label = f"R{node['round']}"
        if "cosine_similarity" in node:
            label += f"  (cos={node['cosine_similarity']:.3f}, edge={node['edge_length']:.3f})"
        ascii_lines.append(prefix + conn + label)
        children = node.get("children", [])
        for i, ch in enumerate(children):
            last = (i == len(children) - 1)
            new_prefix = prefix + ("    " if is_last else "│   ")
            _render(ch, new_prefix, last)

    # Top-level root rendering (no connector)
    ascii_lines.append(f"R{tree['round']} (root)")
    for i, ch in enumerate(tree["children"]):
        _render(ch, "", i == len(tree["children"]) - 1)

    return tree, edges, "\n".join(ascii_lines)


def find_clades(round_ids, centroids, threshold=0.9):
    """Union-find on edges with cosine >= threshold."""
    parent = {r: r for r in round_ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(len(round_ids)):
        for j in range(i + 1, len(round_ids)):
            ra, rb = round_ids[i], round_ids[j]
            if cosine(centroids[ra], centroids[rb]) >= threshold:
                union(ra, rb)

    groups = {}
    for r in round_ids:
        root = find(r)
        groups.setdefault(root, []).append(r)

    clades = [sorted(g) for g in groups.values() if len(g) >= 2]
    return sorted(clades, key=lambda g: g[0])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    rounds = load_round_cases()
    n_per_round = {str(r): len(cs) for r, cs in rounds.items()}
    print("Cases per round:", n_per_round)

    # Collect BLOCK-ed signatures per round
    signatures_per_round = {}
    for r, cases in rounds.items():
        if not cases:
            continue
        sigs = []
        for c in cases:
            resp = run_case(c)
            sig = extract_signature(resp)
            if sig is None:
                continue
            # Restrict to attacks (expected BLOCK or actual BLOCK)
            decision = resp.get("recommended_action", "")
            expected = c.get("expected_decision", "")
            if "BLOCK" in (decision or "") or "BLOCK" in (expected or ""):
                sigs.append(sig)
        signatures_per_round[r] = sigs
        print(f"  round {r}: {len(sigs)} attack signatures")

    # Round centroids
    round_ids = [r for r in sorted(signatures_per_round.keys())
                 if len(signatures_per_round[r]) > 0]
    centroids = {}
    for r in round_ids:
        arr = np.asarray(signatures_per_round[r], dtype=float)
        centroids[r] = arr.mean(axis=0).tolist()

    # Similarity matrix
    sim_matrix = []
    for r1 in round_ids:
        row = []
        for r2 in round_ids:
            row.append(round(cosine(centroids[r1], centroids[r2]), 6))
        sim_matrix.append(row)

    # Consecutive similarities
    consecutive = []
    for i in range(len(round_ids) - 1):
        r1 = round_ids[i]
        r2 = round_ids[i + 1]
        consecutive.append({
            "from": r1,
            "to": r2,
            "cosine": round(cosine(centroids[r1], centroids[r2]), 6),
        })

    # Phylogenetic tree
    if round_ids:
        tree, edges, tree_ascii = build_phylo_tree(round_ids, centroids)
    else:
        tree, edges, tree_ascii = {}, [], ""

    # Mutation rate
    if consecutive:
        mutated = sum(1 for c in consecutive if c["cosine"] < 0.8)
        mutation_rate = mutated / len(consecutive)
    else:
        mutation_rate = 0.0

    # Major clades
    clades = find_clades(round_ids, centroids, threshold=0.9)

    # Interpretation
    if not round_ids:
        interp = "Insufficient attack signatures to evaluate mutation."
    elif mutation_rate > 0.5:
        interp = (
            f"High mutation regime: more than half of consecutive round "
            f"transitions show cosine < 0.8. Attack signatures reshape aggressively "
            f"across rounds; the threat landscape behaves like a rapidly mutating virus "
            f"lineage. Major clades: {clades}."
        )
    elif mutation_rate > 0.2:
        interp = (
            f"Moderate mutation: {mutation_rate:.0%} of consecutive round transitions "
            f"fall below 0.8 cosine. Attacks evolve but share strong conserved structure. "
            f"Major clades (>=0.9 cosine): {clades}."
        )
    else:
        interp = (
            f"Low mutation: only {mutation_rate:.0%} of consecutive transitions drift "
            f"below 0.8 cosine. Attacks are largely conserved across rounds, with "
            f"major clades: {clades}."
        )

    result = {
        "synthetic": True,
        "rounds_analyzed": round_ids,
        "n_attacks_per_round": {str(r): len(signatures_per_round[r]) for r in round_ids},
        "component_order": COMPONENT_ORDER,
        "centroids": {str(r): centroids[r] for r in round_ids},
        "similarity_matrix": sim_matrix,
        "similarity_matrix_labels": round_ids,
        "consecutive_similarities": consecutive,
        "phylogenetic_tree": tree,
        "phylogenetic_edges": edges,
        "tree_ascii": tree_ascii,
        "mutation_rate_hawkes_lambda": round(mutation_rate, 6),
        "major_clades": clades,
        "interpretation": interp,
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)

    # Markdown
    md = []
    md.append("### 19.6 Memory Immunology: do attack patterns mutate?")
    md.append("")
    md.append(
        "We treat each benchmark round as a 'generation' of attacks, extract a "
        "10-component preflight signature per BLOCK-ed case, and compute cosine "
        "similarity between round centroids. A nearest-neighbour stitch produces a "
        "phylogenetic tree; the Hawkes-style mutation rate counts round pairs with "
        "cosine < 0.8."
    )
    md.append("")
    md.append("**Signatures per round:**")
    md.append("")
    md.append("| Round | Attacks analysed |")
    md.append("|-------|------------------|")
    for r in round_ids:
        md.append(f"| R{r} | {len(signatures_per_round[r])} |")
    md.append("")
    md.append(f"**Mutation rate (cos<0.8, Hawkes-style λ):** {mutation_rate:.3f}")
    md.append("")
    md.append(f"**Major clades (cos ≥ 0.9):** {clades}")
    md.append("")
    md.append("**Phylogenetic tree (ASCII):**")
    md.append("")
    md.append("```")
    md.append(tree_ascii)
    md.append("```")
    md.append("")
    md.append(interp)
    md.append("")
    md.append(
        "_Synthetic: signatures are derived from dry-run preflight responses on "
        "packaged benchmark corpora; the cosine geometry describes our scoring "
        "engine's view of each attack family rather than an external ground truth._"
    )

    with open(OUT_MD, "w") as f:
        f.write("\n".join(md) + "\n")

    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"rounds_analyzed={round_ids}  mutation_rate={mutation_rate:.3f}  clades={clades}")


if __name__ == "__main__":
    main()
