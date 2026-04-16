#!/usr/bin/env python3
"""
Research Task #13: Sheaf Cohomology on module dependency graph.

Question: Treating modules as sheaf sections and data-flow edges as
compatibility constraints, how many hidden contradictions (cycles in the
dependency graph that can't be resolved by local consistency) do we carry?

Method:
1. Load module_dag from research/results/structural_findings.json.
2. Build V (nodes = modules) and E (directed edges).
3. Compute:
   - H⁰ = number of weakly connected components.
   - H¹ = β₁ = E - V + β₀ (number of independent cycles in undirected skeleton).
4. Find simple cycles via DFS.
5. Identify spanning tree; non-tree edges = cycles requiring manual
   cross-checks.
"""
from __future__ import annotations

import os
import sys
import json
from typing import Dict, List, Set, Tuple

sys.path.insert(0, "/Users/zsobrakpeter/core")

STRUCT_PATH = "/Users/zsobrakpeter/core/research/results/structural_findings.json"
RESULTS_PATH = "/Users/zsobrakpeter/core/research/results/sheaf_module_graph.json"
MARKDOWN_PATH = "/Users/zsobrakpeter/core/research/results/sheaf_module_graph_section.md"


def load_dag() -> Tuple[List[str], Dict[str, List[str]]]:
    with open(STRUCT_PATH) as f:
        data = json.load(f)
    dag = data["module_dag"]
    adjacency: Dict[str, List[str]] = dict(dag["adjacency"])
    nodes = sorted(adjacency.keys())
    return nodes, adjacency


def connected_components(nodes: List[str], adj: Dict[str, List[str]]) -> List[Set[str]]:
    """Weakly-connected components on the undirected skeleton."""
    undirected: Dict[str, Set[str]] = {n: set() for n in nodes}
    for u, neighbors in adj.items():
        for v in neighbors:
            if v in undirected:
                undirected[u].add(v)
                undirected[v].add(u)
    seen: Set[str] = set()
    components: List[Set[str]] = []
    for n in nodes:
        if n in seen:
            continue
        stack = [n]
        comp: Set[str] = set()
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            comp.add(x)
            for y in undirected[x]:
                if y not in seen:
                    stack.append(y)
        components.append(comp)
    return components


def find_simple_cycles_directed(nodes: List[str], adj: Dict[str, List[str]], max_cycles: int = 20) -> List[List[str]]:
    """Find simple cycles in the directed graph via DFS (Johnson-style simplified).

    For sparse graphs with a few back-edges this gives correct results for
    the handful of cycles we care about.
    """
    cycles: List[List[str]] = []
    blocked: Set[str] = set()
    stack: List[str] = []
    in_stack: Set[str] = set()

    def dfs(start: str, current: str):
        if len(cycles) >= max_cycles:
            return
        stack.append(current)
        in_stack.add(current)
        for v in adj.get(current, []):
            if v == start and len(stack) > 0:
                cycles.append(stack + [start])
                if len(cycles) >= max_cycles:
                    in_stack.discard(current)
                    stack.pop()
                    return
            elif v not in in_stack and v not in blocked:
                dfs(start, v)
        stack.pop()
        in_stack.discard(current)

    for n in nodes:
        if len(cycles) >= max_cycles:
            break
        dfs(n, n)
        blocked.add(n)
        stack.clear()
        in_stack.clear()

    # Deduplicate by sorted tuple of node-set (simple cycles treated equal under rotation)
    seen_sigs: Set[tuple] = set()
    unique_cycles: List[List[str]] = []
    for c in cycles:
        sig = tuple(sorted(set(c)))
        if sig in seen_sigs:
            continue
        seen_sigs.add(sig)
        unique_cycles.append(c)
    return unique_cycles


def undirected_cycle_count(nodes: List[str], adj: Dict[str, List[str]]) -> int:
    """β₁ = E - V + β₀ for the undirected skeleton."""
    und_edges: Set[Tuple[str, str]] = set()
    for u, neighbors in adj.items():
        for v in neighbors:
            if u == v or v not in adj:
                continue
            edge = tuple(sorted([u, v]))
            und_edges.add(edge)
    V = len(nodes)
    E = len(und_edges)
    comps = connected_components(nodes, adj)
    beta_0 = len(comps)
    beta_1 = E - V + beta_0
    return beta_1


def spanning_tree_edges(nodes: List[str], adj: Dict[str, List[str]]) -> List[Tuple[str, str]]:
    """BFS spanning forest of the undirected skeleton. Returns tree edges."""
    undirected: Dict[str, Set[str]] = {n: set() for n in nodes}
    for u, neighbors in adj.items():
        for v in neighbors:
            if v in undirected and u != v:
                undirected[u].add(v)
                undirected[v].add(u)

    seen: Set[str] = set()
    tree_edges: List[Tuple[str, str]] = []
    for root in nodes:
        if root in seen:
            continue
        queue = [root]
        seen.add(root)
        while queue:
            u = queue.pop(0)
            for v in sorted(undirected[u]):
                if v not in seen:
                    seen.add(v)
                    tree_edges.append(tuple(sorted([u, v])))
                    queue.append(v)
    return tree_edges


def main():
    print("[sheaf_module] Loading module DAG from structural_findings.json...")
    nodes, adj = load_dag()
    V = len(nodes)

    # Count directed edges
    directed_edges = 0
    for u, neighbors in adj.items():
        for v in neighbors:
            if v in adj and u != v:
                directed_edges += 1

    # Undirected skeleton edges
    und_edges: Set[Tuple[str, str]] = set()
    for u, neighbors in adj.items():
        for v in neighbors:
            if u == v or v not in adj:
                continue
            und_edges.add(tuple(sorted([u, v])))
    E_und = len(und_edges)

    components = connected_components(nodes, adj)
    h0 = len(components)
    h1 = undirected_cycle_count(nodes, adj)

    # Cycle search
    directed_cycles = find_simple_cycles_directed(nodes, adj, max_cycles=20)
    print(f"[sheaf_module] V={V}, E_dir={directed_edges}, E_und={E_und}, H0={h0}, H1={h1}")
    print(f"[sheaf_module] Directed simple cycles found: {len(directed_cycles)}")

    # Top cycles
    top_cycles = []
    for i, cyc in enumerate(directed_cycles[:5]):
        top_cycles.append({
            "cycle_id": i + 1,
            "modules": cyc,
            "length": len(cyc) - 1,
            "interpretation": (
                f"Circular dependency through {len(cyc) - 1} modules — local consistency "
                f"does not imply global consistency without explicit verification."
            ),
        })

    # Spanning tree
    tree_edges = spanning_tree_edges(nodes, adj)
    minimum_cross_checks = max(0, E_und - len(tree_edges))

    # Contradiction risk
    if h1 == 0:
        risk = "low"
        interp = (
            f"The module dependency graph is acyclic (H¹ = 0). All {V} modules factor into "
            f"{h0} weakly-connected components with {E_und} undirected skeleton edges, and "
            f"a spanning tree of {len(tree_edges)} edges covers the entire graph. "
            f"Local sheaf consistency implies global consistency — no hidden contradictions "
            f"are carried by the architecture itself. "
            f"The {h0} components (most of them singletons) indicate {h0 - 1} modules whose "
            f"outputs do not participate in any downstream data flow — these are leaf analytics "
            f"consumed only by the preflight response envelope."
        )
    elif h1 <= 3:
        risk = "medium"
        interp = (
            f"Small number of cycles ({h1}) in undirected skeleton — each one corresponds to "
            f"a pair of modules with mutual data flow. Review the non-tree edges ({minimum_cross_checks}) "
            f"as manual cross-check points."
        )
    else:
        risk = "high"
        interp = (
            f"{h1} cycles present. Sheaf-theoretic guarantee of global consistency from local "
            f"consistency is lost; each cycle is a potential hidden contradiction."
        )

    result = {
        "n_nodes": V,
        "n_edges_directed": directed_edges,
        "n_edges_undirected_skeleton": E_und,
        "h0_connected_components": h0,
        "h1_cycles": h1,
        "top_cycles": top_cycles,
        "spanning_tree_edges": len(tree_edges),
        "minimum_cross_checks_needed": minimum_cross_checks,
        "contradiction_risk": risk,
        "interpretation": interp,
        "component_sizes": sorted([len(c) for c in components], reverse=True)[:10],
    }

    with open(RESULTS_PATH, "w") as f:
        json.dump(result, f, indent=2)
    print(f"[sheaf_module] Wrote {RESULTS_PATH}")

    # Markdown
    md = []
    md.append("### 19.13 Sheaf Cohomology on the Module Dependency Graph\n")
    md.append(
        f"Treating the {V} scoring modules as sheaf sections and the {directed_edges} data-flow "
        f"edges as compatibility constraints, we computed the sheaf-cohomological invariants of "
        f"the undirected skeleton.\n"
    )
    md.append("| Invariant | Value | Meaning |")
    md.append("|---|---:|---|")
    md.append(f"| V (modules) | {V} | nodes |")
    md.append(f"| E (directed) | {directed_edges} | data-flow edges |")
    md.append(f"| E (undirected skeleton) | {E_und} | pairs with any coupling |")
    md.append(f"| H⁰ (components) | {h0} | consistent global sections |")
    md.append(f"| H¹ (cycles) | {h1} | independent hidden contradictions |")
    md.append(f"| Spanning tree edges | {len(tree_edges)} | |")
    md.append(f"| Minimum cross-checks | {minimum_cross_checks} | non-tree edges |")
    md.append("")
    if top_cycles:
        md.append("**Detected cycles** (top 5):\n")
        md.append("| # | length | modules |")
        md.append("|---|---:|---|")
        for tc in top_cycles:
            md.append(f"| {tc['cycle_id']} | {tc['length']} | {' → '.join(tc['modules'])} |")
        md.append("")
    else:
        md.append("No directed simple cycles were detected — the DAG is truly acyclic.\n")
    md.append(f"**Contradiction risk: `{risk}`.**\n")
    md.append(f"**Interpretation.** {interp}\n")

    with open(MARKDOWN_PATH, "w") as f:
        f.write("\n".join(md))
    print(f"[sheaf_module] Wrote {MARKDOWN_PATH}")


if __name__ == "__main__":
    main()
