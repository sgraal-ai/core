"""
Structural Findings A
- TASK 6: 83-module scoring_engine DAG (dependency graph)
- TASK 10: kappa_MEM dollar value (economic break-even)

Outputs to research/results/structural_findings.json
"""
from __future__ import annotations

import ast
import json
import os
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, List, Set, Tuple


REPO_ROOT = Path("/Users/zsobrakpeter/core")
SCORING_DIR = REPO_ROOT / "scoring_engine"
RESULTS_PATH = REPO_ROOT / "research" / "results" / "structural_findings.json"
BUSINESS_METRICS_PATH = REPO_ROOT / "research" / "results" / "business_metrics.json"


# ---------------------------------------------------------------------------
# TASK 6 — module DAG
# ---------------------------------------------------------------------------

def _list_modules() -> List[str]:
    mods: List[str] = []
    for p in sorted(SCORING_DIR.glob("*.py")):
        if p.name == "__init__.py":
            continue
        mods.append(p.stem)
    return mods


def _parse_module_deps(path: Path, known: Set[str]) -> Set[str]:
    """Return set of scoring_engine sibling modules that `path` depends on."""
    deps: Set[str] = set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return deps

    self_name = path.stem

    for node in ast.walk(tree):
        # import scoring_engine.X  /  from scoring_engine import X
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            # from scoring_engine.X import Y
            if mod.startswith("scoring_engine."):
                tail = mod.split(".", 1)[1].split(".", 1)[0]
                if tail in known and tail != self_name:
                    deps.add(tail)
            # from scoring_engine import X, Y
            elif mod == "scoring_engine":
                for alias in node.names:
                    name = alias.name.split(".", 1)[0]
                    if name in known and name != self_name:
                        deps.add(name)
            # from .X import Y  (relative, level >= 1)
            elif node.level and node.level >= 1 and mod:
                tail = mod.split(".", 1)[0]
                if tail in known and tail != self_name:
                    deps.add(tail)
            # from . import X
            elif node.level and node.level >= 1 and not mod:
                for alias in node.names:
                    name = alias.name.split(".", 1)[0]
                    if name in known and name != self_name:
                        deps.add(name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                # import scoring_engine.X
                if name.startswith("scoring_engine."):
                    tail = name.split(".", 1)[1].split(".", 1)[0]
                    if tail in known and tail != self_name:
                        deps.add(tail)
    return deps


def _topological_order(adj: Dict[str, List[str]]) -> List[str]:
    """Return topological order where dependencies come before dependents.
    adj[a] = list of modules that a depends on.
    """
    in_degree = {n: 0 for n in adj}
    reverse: Dict[str, List[str]] = {n: [] for n in adj}
    for a, deps in adj.items():
        for b in deps:
            in_degree[a] += 1
            reverse[b].append(a)

    # Start with nodes that have no deps (leaves in dependency-of sense)
    queue = deque(sorted(n for n, d in in_degree.items() if d == 0))
    order: List[str] = []
    in_deg = dict(in_degree)
    while queue:
        node = queue.popleft()
        order.append(node)
        for dependent in sorted(reverse[node]):
            in_deg[dependent] -= 1
            if in_deg[dependent] == 0:
                queue.append(dependent)
    return order


def _longest_path(adj: Dict[str, List[str]], topo: List[str]) -> Tuple[List[str], int]:
    """Longest chain of dependencies. adj[a] = deps of a.
    Length counts number of nodes on the path.
    """
    # dp[node] = (length, next_dep_in_chain)
    dp: Dict[str, Tuple[int, str | None]] = {}
    # Process in reverse topological order: dependencies first
    for node in topo:
        best_len = 1
        best_next: str | None = None
        for dep in adj.get(node, []):
            if dep in dp:
                cand = dp[dep][0] + 1
                if cand > best_len:
                    best_len = cand
                    best_next = dep
        dp[node] = (best_len, best_next)

    # Find node with maximum dp
    start = max(dp.keys(), key=lambda n: dp[n][0]) if dp else None
    if start is None:
        return [], 0
    chain: List[str] = []
    cur: str | None = start
    while cur is not None:
        chain.append(cur)
        cur = dp[cur][1]
    return chain, len(chain)


def _parallel_groups(adj: Dict[str, List[str]]) -> List[List[str]]:
    """Kahn layering: each layer = set of modules whose deps all lie in earlier layers.
    Modules within a layer are independent and can run in parallel.
    adj[a] = deps of a.
    """
    remaining = {n: set(deps) for n, deps in adj.items()}
    all_nodes = set(adj.keys())
    layers: List[List[str]] = []
    satisfied: Set[str] = set()
    while remaining:
        # Nodes whose deps are all satisfied
        layer = sorted(n for n, d in remaining.items() if d.issubset(satisfied))
        if not layer:
            # Cycle — break out, put the rest into a final "cycle" layer
            layer = sorted(remaining.keys())
            layers.append(layer)
            break
        layers.append(layer)
        for n in layer:
            satisfied.add(n)
            del remaining[n]
    return layers


def task6_module_dag() -> Dict:
    modules = _list_modules()
    known = set(modules)
    adj: Dict[str, List[str]] = {m: [] for m in modules}
    for m in modules:
        deps = _parse_module_deps(SCORING_DIR / f"{m}.py", known)
        adj[m] = sorted(deps)

    total_modules = len(modules)
    total_edges = sum(len(v) for v in adj.values())

    # In-degree here = # of modules that depend on X (X is depended upon).
    # adj[a] = deps of a. So dependents[x] = { a : x in adj[a] }.
    dependents: Dict[str, int] = {m: 0 for m in modules}
    for a, deps in adj.items():
        for b in deps:
            dependents[b] = dependents.get(b, 0) + 1

    # Topological order (deps before dependents)
    topo = _topological_order(adj)

    # Longest path (critical path in DAG)
    critical_path, critical_path_length = _longest_path(adj, topo)

    # Parallel groups (Kahn layers)
    layers = _parallel_groups(adj)
    layers_sorted_by_size = sorted(layers, key=len, reverse=True)
    top3_groups = layers_sorted_by_size[:3]
    longest_group_size = len(layers_sorted_by_size[0]) if layers_sorted_by_size else 0

    # Bottleneck modules (most dependents)
    bottlenecks = sorted(
        ({"module": m, "dependents": dependents[m]} for m in modules),
        key=lambda x: (-x["dependents"], x["module"]),
    )[:10]

    # Max parallel speedup = total_modules / critical_path_length
    speedup = (total_modules / critical_path_length) if critical_path_length else float(total_modules)

    result = {
        "total_modules": total_modules,
        "total_edges": total_edges,
        "critical_path": critical_path,
        "critical_path_length": critical_path_length,
        "bottleneck_modules": bottlenecks,
        "parallel_groups": top3_groups,
        "max_parallel_speedup": f"{speedup:.2f}x",
        "longest_parallel_group_size": longest_group_size,
        "num_layers": len(layers),
        "adjacency": adj,
    }
    return result


# ---------------------------------------------------------------------------
# TASK 10 — kappa_MEM dollar value
# ---------------------------------------------------------------------------

KAPPA_MEM = 0.033
BLOCK_RATE_AT_THRESHOLD = 0.046
COST_FULL = 0.001  # $/call
COST_LITE = 0.00001  # $/call

SAVINGS_PER_BLOCK = {
    "medical": 3350.0,
    "legal": 1340.0,
    "fintech": 670.0,
    "general": 134.0,
    "coding": 67.0,
    "customer_support": 34.0,
}


def _compute_row(domain: str, savings: float, tier: str, cost: float) -> Dict:
    savings_per_call = BLOCK_RATE_AT_THRESHOLD * savings
    roi_multiplier = savings_per_call / cost
    calls_paid_by_one_block = int(savings / cost)
    annual_calls_break_even = savings / cost  # cost*calls == savings

    profitable = roi_multiplier >= 1.0
    highly = roi_multiplier >= 10.0

    if profitable:
        verdict = (
            f"Every call is profitable. One prevented BLOCK pays for "
            f"{calls_paid_by_one_block:,} calls of governance. "
            f"ROI = {roi_multiplier:,.1f}x per call."
        )
    else:
        verdict = (
            f"Governance cost exceeds per-call expected savings. "
            f"ROI = {roi_multiplier:.3f}x. Break-even at annual volume "
            f"{annual_calls_break_even:,.0f} calls per prevented failure."
        )

    return {
        "domain": domain,
        "tier": tier,
        "savings_per_call": round(savings_per_call, 6),
        "cost_per_call": cost,
        "roi_multiplier_per_call": round(roi_multiplier, 4),
        "calls_paid_by_one_block": calls_paid_by_one_block,
        "break_even_annual_call_volume": round(annual_calls_break_even, 2),
        "profitable_from_call_1": profitable,
        "roi_above_10x": highly,
        "break_even_analysis": verdict,
    }


def task10_kappa_mem_dollar_value() -> Dict:
    per_domain_tier: Dict[str, Dict] = {}
    for domain, savings in SAVINGS_PER_BLOCK.items():
        per_domain_tier[f"{domain}_lite"] = _compute_row(domain, savings, "lite", COST_LITE)
        per_domain_tier[f"{domain}_full"] = _compute_row(domain, savings, "full", COST_FULL)

    # Headline verdict
    all_profitable = all(v["profitable_from_call_1"] for v in per_domain_tier.values())
    all_above_10x = all(v["roi_above_10x"] for v in per_domain_tier.values())

    if all_above_10x:
        verdict_headline = "At every tested domain x tier, governance ROI > 10x per call. Governance is economically inevitable from call #1."
    elif all_profitable:
        profitable_above_10x = [k for k, v in per_domain_tier.items() if v["roi_above_10x"]]
        verdict_headline = (
            f"Every domain x tier is profitable from call #1. "
            f"ROI > 10x in: {', '.join(sorted(profitable_above_10x))}."
        )
    else:
        unprofitable = [k for k, v in per_domain_tier.items() if not v["profitable_from_call_1"]]
        profitable_above_10x = [k for k, v in per_domain_tier.items() if v["roi_above_10x"]]
        verdict_headline = (
            f"Per-call governance is unprofitable for: {', '.join(sorted(unprofitable))}. "
            f"Highly profitable (ROI > 10x) for: {', '.join(sorted(profitable_above_10x))}."
        )

    return {
        "kappa_mem": KAPPA_MEM,
        "block_rate_at_threshold": BLOCK_RATE_AT_THRESHOLD,
        "cost_per_call": {"full": COST_FULL, "lite": COST_LITE},
        "savings_per_block": SAVINGS_PER_BLOCK,
        "per_domain_tier": per_domain_tier,
        "economic_verdict": verdict_headline,
    }


# ---------------------------------------------------------------------------
# Merge + write
# ---------------------------------------------------------------------------

def _load_existing(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _print_summary(dag: Dict, kappa: Dict) -> None:
    print("=" * 72)
    print("TASK 6 — 83-module DAG")
    print("=" * 72)
    print(f"Total modules: {dag['total_modules']}")
    print(f"Total edges:   {dag['total_edges']}")
    print(f"Critical path length: {dag['critical_path_length']}")
    print(f"Critical path: {' -> '.join(dag['critical_path'])}")
    print(f"Max parallel speedup: {dag['max_parallel_speedup']}")
    print(f"Longest parallel group size: {dag['longest_parallel_group_size']}")
    print(f"Kahn layers (sequential depth): {dag['num_layers']}")
    print("\nTop 10 bottleneck modules:")
    for b in dag["bottleneck_modules"]:
        print(f"  {b['module']:<30s}  dependents={b['dependents']}")
    print("\nTop 3 parallel groups (size first):")
    for i, g in enumerate(dag["parallel_groups"], 1):
        print(f"  Group {i} (size={len(g)}): {', '.join(g[:10])}" + (" ..." if len(g) > 10 else ""))

    print()
    print("=" * 72)
    print("TASK 10 — kappa_MEM dollar value")
    print("=" * 72)
    print(f"kappa_MEM: {kappa['kappa_mem']}")
    print(f"BLOCK rate at threshold: {kappa['block_rate_at_threshold']}")
    print(f"Cost per call: full=${COST_FULL}, lite=${COST_LITE}")
    print()
    print(f"{'domain_tier':<26s}{'ROI/call':>14s}{'calls/1 BLOCK':>20s}{'profitable':>14s}")
    print("-" * 74)
    for key, row in kappa["per_domain_tier"].items():
        print(
            f"{key:<26s}"
            f"{row['roi_multiplier_per_call']:>14,.2f}"
            f"{row['calls_paid_by_one_block']:>20,d}"
            f"{str(row['profitable_from_call_1']):>14s}"
        )
    print()
    print(f"Verdict: {kappa['economic_verdict']}")


def main() -> None:
    dag = task6_module_dag()
    kappa = task10_kappa_mem_dollar_value()

    existing = _load_existing(RESULTS_PATH)
    existing["module_dag"] = dag
    existing["kappa_mem_dollar_value"] = kappa

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    _print_summary(dag, kappa)
    print(f"\nWrote: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
