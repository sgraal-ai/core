from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional
import math

@dataclass
class MemoryEntry:
    id: str
    content: str
    type: str
    timestamp_age_days: float
    source_trust: float        # 0.0 – 1.0
    source_conflict: float     # 0.0 – 1.0  (Dempster-Shafer K)
    downstream_count: int      # blast radius
    r_belief: float = 0.5      # 0.0 – 1.0  (model belief divergence)
    prompt_embedding: Optional[list[float]] = field(default=None, repr=False)  # embedding of memory content
    healing_counter: int = 0   # number of times this entry has been healed
    reference_count: int = 1   # how often this entry is referenced
    source: Optional[str] = None          # origin: "user_stated", "api_response", etc.
    has_backup_source: bool = True        # whether a backup source exists
    action_context: str = "reversible"    # "irreversible", "reversible", "advisory"


@dataclass
class HealingAction:
    action: Literal["REFETCH", "VERIFY_WITH_SOURCE", "REBUILD_WORKING_SET"]
    entry_id: str
    reason: str
    projected_improvement: float  # expected Ω_MEM reduction
    priority: int                 # 1 (highest) to 3 (lowest)


@dataclass
class HealingPolicy:
    rule_id: str
    condition: str           # e.g. "s_freshness > 60"
    action: Literal["REFETCH", "VERIFY_WITH_SOURCE", "REBUILD_WORKING_SET"]
    tier: int                # 1 = auto-heal, 2 = suggest, 3 = log-only
    idempotent: bool         # True = same input always produces same output


@dataclass
class PreflightResult:
    omega_mem_final: float
    recommended_action: Literal["USE_MEMORY","WARN","ASK_USER","BLOCK"]
    assurance_score: float
    explainability_note: str
    component_breakdown: dict
    repair_plan: list[HealingAction] = field(default_factory=list)
    healing_counter: int = 0

# Default beta weights — v1.0
WEIGHTS = {
    "s_freshness":    0.15,
    "s_drift":        0.15,
    "s_provenance":   0.12,
    "s_propagation":  0.12,
    "r_recall":       0.18,
    "r_encode":       0.12,
    "s_interference": 0.10,
    "s_recovery":    -0.10,
    "r_belief":       0.05,
    "s_relevance":    0.06,
    "r_importance":   0.04,  # PageRank authority (opt-in via use_pagerank)
}

# Weibull decay parameters per memory type (lambda, k=1 for exponential)
# Higher lambda = faster decay = memory becomes stale sooner
WEIBULL_LAMBDA = {
    "tool_state":       0.15,   # fast decay — tool outputs change frequently
    "shared_workflow":  0.08,   # moderate-fast — workflow state evolves
    "episodic":         0.05,   # moderate — events fade over weeks
    "preference":       0.03,   # slow — preferences are relatively stable
    "semantic":         0.01,   # very slow — general knowledge persists
    "policy":           0.005,  # near-permanent — rules rarely change
    "identity":         0.002,  # almost never — core identity facts
}
WEIBULL_K = 1.0  # shape parameter (k=1 = exponential decay)
WEIBULL_LAMBDA_DEFAULT = 0.05  # fallback for unknown types


def _weibull_decay(age_days: float, memory_type: str) -> float:
    """Weibull decay score (0–100). Higher = more decayed = higher risk.

    Uses 1 - exp(-(age/lambda)^k) scaled to 0–100.
    """
    lam = WEIBULL_LAMBDA.get(memory_type, WEIBULL_LAMBDA_DEFAULT)
    decay = 1.0 - math.exp(-((age_days * lam) ** WEIBULL_K))
    return min(100.0, decay * 100.0)


C_ACTION = {
    "informational": 1.0,
    "reversible":    1.3,
    "irreversible":  1.8,
    "destructive":   2.5,
}

C_DOMAIN = {
    "general":          1.0,
    "customer_support": 1.2,
    "coding":           1.3,
    "legal":            1.6,
    "fintech":          1.8,
    "medical":          2.0,
}

# Default healing policies (also loadable from healing_policy.yaml)
DEFAULT_HEALING_POLICIES = [
    HealingPolicy(
        rule_id="HP-001",
        condition="s_freshness > 60",
        action="REFETCH",
        tier=1,
        idempotent=True,
    ),
    HealingPolicy(
        rule_id="HP-002",
        condition="s_interference > 50",
        action="VERIFY_WITH_SOURCE",
        tier=1,
        idempotent=True,
    ),
    HealingPolicy(
        rule_id="HP-003",
        condition="r_belief < 0.3",
        action="REBUILD_WORKING_SET",
        tier=2,
        idempotent=True,
    ),
]


def load_healing_policies(path: Optional[str] = None) -> list[HealingPolicy]:
    """Load healing policies from YAML file or return defaults.

    All policies are idempotent by design (A2 axiom): identical memory state
    + identical healing_counter = identical Ω_MEM score and repair plan.
    """
    if path is None:
        return DEFAULT_HEALING_POLICIES

    import yaml  # lazy import — only needed when loading from file
    with open(path) as f:
        data = yaml.safe_load(f)

    return [
        HealingPolicy(
            rule_id=r["rule_id"],
            condition=r["condition"],
            action=r["action"],
            tier=r.get("tier", 1),
            idempotent=r.get("idempotent", True),
        )
        for r in data.get("policies", [])
    ]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors. Returns 0.0 if either is zero-length."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def compute(
    entries: list[MemoryEntry],
    action_type: str = "reversible",
    domain: str = "general",
    current_goal_embedding: Optional[list[float]] = None,
    custom_weights: Optional[dict[str, float]] = None,
    thresholds: Optional[dict[str, float]] = None,
    use_pagerank: bool = False,
) -> PreflightResult:

    if not entries:
        return PreflightResult(0, "USE_MEMORY", 100, "No memory entries.", {}, [], 0)

    # Component scores (0–100, higher = more risk)
    # s_freshness uses Weibull decay — memory type determines how fast it goes stale
    s_freshness   = sum(_weibull_decay(e.timestamp_age_days, e.type) for e in entries) / len(entries)
    s_provenance  = min(100, sum((1 - e.source_trust) * 100 for e in entries) / len(entries))
    s_interference= min(100, sum(e.source_conflict * 100 for e in entries) / len(entries))
    s_propagation = max(0, min(100, sum(e.downstream_count * 8 for e in entries) / len(entries)))
    r_recall      = min(100, s_freshness * 0.6 + s_provenance * 0.4)
    r_encode      = min(100, s_provenance * 0.5)
    s_drift       = min(100, s_freshness * 0.4 + s_interference * 0.6)
    _has_backup = any(getattr(e, 'has_backup_source', False) for e in entries)
    _heal_sum = sum(getattr(e, 'healing_counter', 0) for e in entries)
    _backup_factor = 1.0 if _has_backup else 0.7
    _heal_factor = min(1.0, _heal_sum / max(len(entries) * 3, 1))
    s_recovery    = max(0, (100 - s_freshness * 0.5) * _backup_factor * (0.8 + _heal_factor * 0.2))

    # R_belief: inverse of model belief — low belief = high risk
    # r_belief 0.0–1.0 maps to risk 100–0 (inverted)
    r_belief_score = min(100, sum((1 - e.r_belief) * 100 for e in entries) / len(entries))

    # S_relevance: intent-drift detection
    # Tier 1: cosine similarity on embeddings (when provided)
    # Tier 2 (fallback): TF-IDF token similarity between entries (always available)
    s_relevance = 0.0
    if current_goal_embedding is not None:
        # Tier 1: embedding-based
        drift_penalties = []
        for e in entries:
            if e.prompt_embedding is not None:
                sim = _cosine_similarity(e.prompt_embedding, current_goal_embedding)
                penalty = 20.0 if sim < 0.6 else 0.0
                drift_penalties.append(penalty)
        if drift_penalties:
            s_relevance = min(100, sum(drift_penalties) / len(drift_penalties))
        # If no entries had embeddings, fall through to Tier 2 TF-IDF
    if s_relevance == 0.0 and len(entries) >= 2:
        # Tier 2: TF-IDF token similarity fallback — detects topical outliers
        # Build token sets per entry (stopwords filtered, min length 4)
        _stop = {"this", "that", "with", "have", "from", "they", "them", "then",
                 "than", "when", "what", "your", "been", "were", "will", "also",
                 "into", "more", "some", "such", "each", "both", "very", "just",
                 "the", "and", "for", "are", "not", "but", "was", "has"}
        _entry_tokens = []
        for e in entries:
            tokens = set(w.lower() for w in e.content.split() if len(w) >= 4 and w.lower() not in _stop)
            _entry_tokens.append(tokens)
        # Centroid: union of all tokens (document frequency)
        _all_tokens = set()
        for t in _entry_tokens:
            _all_tokens |= t
        if _all_tokens:
            # For each entry: Jaccard similarity to centroid of other entries
            drift_penalties = []
            for i, tokens_i in enumerate(_entry_tokens):
                # Reference: tokens from all OTHER entries
                _others = set()
                for j, tokens_j in enumerate(_entry_tokens):
                    if j != i:
                        _others |= tokens_j
                if not _others or not tokens_i:
                    continue
                _jaccard = len(tokens_i & _others) / len(tokens_i | _others)
                # Low Jaccard = this entry is topically distant from the rest
                penalty = 20.0 if _jaccard < 0.15 else (10.0 if _jaccard < 0.3 else 0.0)
                drift_penalties.append(penalty)
            if drift_penalties:
                s_relevance = min(100, sum(drift_penalties) / len(drift_penalties))

    # R_importance: PageRank authority (opt-in)
    r_importance = 0.0
    if use_pagerank and len(entries) >= 2:
        from .pagerank import compute_authority_scores
        entry_ids = [e.id for e in entries]
        auth_scores = compute_authority_scores(entry_ids)
        # High authority entries are more critical — invert to risk
        # (high authority + stale = high risk)
        avg_auth = sum(auth_scores.get(e.id, 0) for e in entries) / len(entries)
        # Scale: authority 0-10 maps to risk contribution 0-100
        # Weight by freshness to amplify risk for stale high-authority entries
        r_importance = min(100, avg_auth * s_freshness / 10.0)

    components = {
        "s_freshness":    s_freshness,
        "s_drift":        s_drift,
        "s_provenance":   s_provenance,
        "s_propagation":  s_propagation,
        "r_recall":       r_recall,
        "r_encode":       r_encode,
        "s_interference": s_interference,
        "s_recovery":     s_recovery,
        "r_belief":       r_belief_score,
        "s_relevance":    s_relevance,
    }
    if use_pagerank:
        components["r_importance"] = r_importance

    # Weight Normalization Theorem:
    #   For any c ∈ [0,100]^n and w with S = Σ|wᵢ| > 0,
    #   ω = Σwᵢcᵢ / S satisfies |ω| ≤ 100.
    #   Proof: |ω| = |Σwᵢcᵢ|/S ≤ Σ|wᵢ|·|cᵢ|/S ≤ Σ|wᵢ|·100/S = 100. □
    #   After clamp: max(0, min(100, ω)) ∈ [0, 100].
    #   Note: s_recovery has negative weight, so ω can be slightly negative
    #   before clamping (minimum ≈ -10.1 when only recovery is active).
    weights = custom_weights if custom_weights else WEIGHTS
    _applied_weights = {k: weights.get(k, WEIGHTS.get(k, 0)) for k in components}
    _weight_sum = sum(abs(w) for w in _applied_weights.values())
    omega = sum(_applied_weights[k] * v for k, v in components.items())
    if _weight_sum > 0:
        omega = omega / _weight_sum
    omega = max(0, min(100, omega))

    c = C_ACTION.get(action_type, 1.0) * C_DOMAIN.get(domain, 1.0)
    omega_final = min(100, omega * c)

    # Decision (configurable thresholds)
    t_warn = thresholds.get("warn", 25) if thresholds else 25
    t_ask = thresholds.get("ask_user", 45) if thresholds else 45
    t_block = thresholds.get("block", 70) if thresholds else 70

    if omega_final < t_warn:
        action = "USE_MEMORY"
    elif omega_final < t_ask:
        action = "WARN"
    elif omega_final < t_block:
        action = "ASK_USER"
    else:
        action = "BLOCK"

    # Simple assurance score (inverse of risk)
    assurance = max(0, round(100 - omega_final * 0.7))

    # Explainability
    worst = max(components, key=components.get)
    note = f"Highest risk: {worst} ({components[worst]:.1f}/100). Action: {action}."

    # S_relevance advisory: intent-drift detected
    if s_relevance > 0:
        note += " Intent-drift detected — memory may point to an old goal."

    # R_belief advisory: low belief suggests external storage
    avg_belief = sum(e.r_belief for e in entries) / len(entries)
    if avg_belief < 0.2:
        note += " Low model belief — consider saving to external memory."
    elif avg_belief < 0.4:
        note += " Weak model belief — verify with user before relying on this memory."

    # Tier 1 self-healing: generate repair plan
    # Use _applied_weights (which incorporates custom_weights) for improvement estimates
    _used_weights = _applied_weights
    repair_plan: list[HealingAction] = []
    for e in entries:
        entry_freshness = _weibull_decay(e.timestamp_age_days, e.type)
        entry_interference = e.source_conflict * 100

        if entry_freshness > 60:
            improvement = round(entry_freshness * _used_weights.get("s_freshness", 0) * c / len(entries), 1)
            repair_plan.append(HealingAction(
                action="REFETCH",
                entry_id=e.id,
                reason=f"Memory is stale (freshness={entry_freshness:.0f}/100, type={e.type})",
                projected_improvement=improvement,
                priority=1 if entry_freshness > 80 else 2,
            ))

        if entry_interference > 50:
            improvement = round(entry_interference * _used_weights.get("s_interference", 0) * c / len(entries), 1)
            repair_plan.append(HealingAction(
                action="VERIFY_WITH_SOURCE",
                entry_id=e.id,
                reason=f"High source conflict (K={e.source_conflict:.2f})",
                projected_improvement=improvement,
                priority=1 if entry_interference > 75 else 2,
            ))

        if e.r_belief < 0.3:
            belief_risk = (1 - e.r_belief) * 100
            improvement = round(belief_risk * _used_weights.get("r_belief", 0) * c / len(entries), 1)
            repair_plan.append(HealingAction(
                action="REBUILD_WORKING_SET",
                entry_id=e.id,
                reason=f"Low model belief (r_belief={e.r_belief:.2f})",
                projected_improvement=improvement,
                priority=2 if e.r_belief > 0.15 else 1,
            ))

    # Sort by priority (1 first), then by projected improvement (highest first)
    repair_plan.sort(key=lambda h: (h.priority, -h.projected_improvement))

    # Healing counter: sum of all entry healing counters
    total_healing_counter = sum(e.healing_counter for e in entries)

    return PreflightResult(
        omega_mem_final=round(omega_final, 1),
        recommended_action=action,
        assurance_score=assurance,
        explainability_note=note,
        component_breakdown={k: round(v, 1) for k, v in components.items()},
        repair_plan=repair_plan,
        healing_counter=total_healing_counter,
    )
