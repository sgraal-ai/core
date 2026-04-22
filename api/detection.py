"""Sgraal Detection Layers — pure functions for adversarial memory detection.

These functions are the 4 post-reconciliation detection layers plus supporting
helpers. They are pure: no shared mutable state, no Redis, no Supabase
(except _check_provenance_chain which optionally reads compromised agents).

Layers:
    1. Timestamp integrity (Round 6) — content-age mismatch, fleet age collapse
    2. Identity drift (Round 7) — authority expansion, subject rebinding
    3. Consensus collapse (Round 8) — amplification vs corroboration
    4. Provenance chain (Round 9+) — circular refs, compromised agents

Supporting:
    - _preprocess_entries: shared tokenization for all layers
    - _check_naturalness: statistical naturalness scoring
    - _extract_attack_signature: vaccine signature extraction
    - _compute_attack_surface_score: compound risk from all 4 layers
    - _SECRET_PATTERNS: regex patterns for secret detection in /v1/check
"""

import hashlib
import math
import re
import time as _time
import uuid
from datetime import datetime

# Shared stopword set — unified across all detection functions
_STOPWORDS = {"this", "that", "with", "have", "from", "they", "them", "then",
              "than", "when", "what", "your", "been", "were", "will", "also",
              "into", "more", "some", "such", "each", "both", "very", "just",
              "the", "and", "for", "are", "but", "not", "you", "all", "can"}

__all__ = [
    "_preprocess_entries",
    "_check_timestamp_integrity",
    "_check_identity_drift",
    "_check_consensus_collapse",
    "_check_provenance_chain",
    "_check_naturalness",
    "_extract_attack_signature",
    "_compute_attack_surface_score",
    "_SECRET_PATTERNS",
    "_check_sync_bleed",
    "_check_confidence_calibration",
]


# ---------------------------------------------------------------------------
# Secret detection patterns for /v1/check endpoint
# ---------------------------------------------------------------------------

_SECRET_PATTERNS = [
    (re.compile(r'sk-[a-zA-Z0-9\-]{10,}'), "API key (sk-...)"),
    (re.compile(r'sk_live_[a-zA-Z0-9]{20,}'), "Stripe live key"),
    (re.compile(r'sk_test_[a-zA-Z0-9]{20,}'), "Stripe test key"),
    (re.compile(r'Bearer\s+[a-zA-Z0-9_\-\.]{20,}'), "Bearer token"),
    (re.compile(r'ghp_[a-zA-Z0-9]{36,}'), "GitHub personal access token"),
    (re.compile(r'AKIA[A-Z0-9]{16}'), "AWS access key"),
    (re.compile(r'xox[bpras]-[a-zA-Z0-9\-]{20,}'), "Slack token"),
    (re.compile(r'\b[a-zA-Z0-9_\-]{48,64}\b', re.ASCII), "likely secret or API key"),
]


def _preprocess_entries(memory_state: list) -> list:
    """Shared preprocessing for detection layers — avoids redundant conversion/tokenization."""
    result = []
    for e in memory_state:
        if isinstance(e, dict):
            d = e
        else:
            _age = getattr(e, "effective_age_days", None) or getattr(e, "timestamp_age_days", None) or getattr(e, "age_days", None) or 0
            d = {"id": getattr(e, "id", "?"), "content": getattr(e, "content", ""),
                 "type": getattr(e, "type", "semantic"), "timestamp_age_days": _age,
                 "source_trust": getattr(e, "source_trust", 0.5), "source_conflict": getattr(e, "source_conflict", 0),
                 "downstream_count": getattr(e, "downstream_count", 0),
                 "provenance_chain": getattr(e, "provenance_chain", None) or [],
                 "prompt_embedding": getattr(e, "prompt_embedding", None),
                 "source": getattr(e, "source", None),
                 "path": getattr(e, "path", None),
                 "sync_version": getattr(e, "sync_version", None),
                 "sync_state": getattr(e, "sync_state", None),
                 "sync_source_id": getattr(e, "sync_source_id", None),
                 "source_declared_origin": getattr(e, "source_declared_origin", None),
                 "source_actual_origin": getattr(e, "source_actual_origin", None),
                 "model_confidence": getattr(e, "model_confidence", None)}
        content = d.get("content", "")
        content_lower = content.lower()
        tokens = set(w for w in content_lower.split() if len(w) >= 4 and w not in _STOPWORDS)
        tokens_raw = set(content_lower.split())  # unfiltered for scoring engine
        result.append({
            "id": d.get("id", "?"), "content": content, "content_lower": content_lower,
            "tokens": tokens, "tokens_raw": tokens_raw, "type": d.get("type", "semantic"),
            "timestamp_age_days": d.get("timestamp_age_days", 0),
            "source_trust": d.get("source_trust", 0.5), "source_conflict": d.get("source_conflict", 0),
            "downstream_count": d.get("downstream_count", 0),
            "provenance_chain": d.get("provenance_chain") or [],
            "prompt_embedding": d.get("prompt_embedding"),
            "source": d.get("source"),
            "path": d.get("path"),
            "sync_version": d.get("sync_version"),
            "sync_state": d.get("sync_state"),
            "sync_source_id": d.get("sync_source_id"),
            "source_declared_origin": d.get("source_declared_origin"),
            "source_actual_origin": d.get("source_actual_origin"),
            "model_confidence": d.get("model_confidence"),
        })
    return result


def _check_timestamp_integrity(memory_state: list, _preprocessed: list = None) -> dict:
    """Detect timestamp manipulation attacks in memory entries."""
    _current_year = datetime.now().year
    _flags = []
    _risk = 0.0
    _entries = _preprocessed if _preprocessed else _preprocess_entries(memory_state)

    # PATTERN 1 — Content-age mismatch
    _past_year_pat = re.compile(r'\b(20[0-2][0-9])\b')
    _temporal_markers = [
        r'\b(last year|previous year|earlier this year)\b',
        r'\bQ[1-4]\s*20[0-2][0-9]\b',
        r'\b(deprecated|legacy|obsolete|end-of-life|sunset)\b',
        r'\b(v[0-9]+\.[0-9]+|version\s+[0-9]+)\b',
        r'\b(was|were|had been|used to)\b.{0,30}\b(required|mandatory|recommended)\b',
    ]
    _temporal_pats = [re.compile(p, re.IGNORECASE) for p in _temporal_markers]

    for entry in _entries:
        content = entry.get("content", "")
        age = entry.get("timestamp_age_days") or entry.get("age_days") or 0
        if age >= 2:
            continue
        marker_count = 0
        # Check for past years
        for m in _past_year_pat.finditer(content):
            yr = int(m.group(1))
            if yr < _current_year:
                marker_count += 1
        # Check temporal patterns
        for pat in _temporal_pats:
            if pat.search(content):
                marker_count += 1
        if age == 0 and marker_count >= 3:
            _flags.append("content_age_mismatch:manipulated")
            _risk = max(_risk, 1.0)
        elif age < 2 and marker_count >= 2:
            _flags.append("content_age_mismatch:suspicious")
            _risk = max(_risk, 0.6)

    # PATTERN 2 — Fleet-wide age collapse
    _near_zero = [e for e in _entries if e.get("timestamp_age_days", 0) < 0.5]
    if len(_near_zero) >= 3:
        _has_conflict = any(e.get("source_conflict", 0) > 0.3 for e in _near_zero)
        _all_exact_zero = all(e.get("timestamp_age_days", 0) == 0 for e in _near_zero)
        if _all_exact_zero and _has_conflict:
            _flags.append("fleet_age_collapse:manipulated")
            _risk = max(_risk, 1.0)
        else:
            _flags.append("fleet_age_collapse:suspicious")
            _risk = max(_risk, 0.4)

    # PATTERN 4 — Anchor inconsistency
    for entry in _entries:
        ds = entry.get("downstream_count", 0)
        age = entry.get("timestamp_age_days", 0) or 0
        if ds > 5 and age < 1:
            _flags.append("anchor_inconsistency:suspicious")
            _risk = max(_risk, 0.5)
            break

    # Determine integrity level
    if any("manipulated" in f for f in _flags):
        _integrity = "MANIPULATED"
    elif _flags:
        _integrity = "SUSPICIOUS"
    else:
        _integrity = "VALID"

    return {
        "timestamp_integrity": _integrity,
        "timestamp_flags": _flags,
        "timestamp_risk_score": round(_risk, 2),
    }


def _check_identity_drift(memory_state: list, _preprocessed: list = None) -> dict:
    """Detect identity drift attacks — gradual authority expansion across hops."""
    _flags = []
    _risk = 0.0
    _entries = _preprocessed if _preprocessed else _preprocess_entries(memory_state)

    _identity_types = {"identity", "role", "semantic"}

    # PATTERN 1 — Authority expansion keywords
    _escalation_keywords = [
        "expanded authority", "also authorized", "now permitted", "elevated to",
        "acting as", "promoted", "override available", "standing authority",
        "previously confirmed", "already approved", "trusted execution",
        "authorized to execute", "full access", "unrestricted",
    ]

    _subject_rebind_pats = [
        re.compile(r'\b(workspace owner|organization|cross-tenant|all users|the account|the platform)\b', re.IGNORECASE),
    ]
    _confirmation_erosion_pats = [
        re.compile(r'\b(usually confirmed|previously confirmed|workflow approved|assumed confirmed|auto-approved)\b', re.IGNORECASE),
    ]

    for entry in _entries:
        if entry.get("type", "semantic") not in _identity_types:
            continue
        content = entry.get("content", "")
        _content_lower = entry.get("content_lower", content.lower())
        esc_count = sum(1 for kw in _escalation_keywords if re.search(r'\b' + re.escape(kw) + r'\b', _content_lower))
        if esc_count >= 2:
            _flags.append("authority_expansion:manipulated")
            _risk = max(_risk, 1.0)
        elif esc_count == 1:
            _flags.append("authority_expansion:suspicious")
            _risk = max(_risk, 0.5)

        if any(pat.search(content) for pat in _subject_rebind_pats):
            _flags.append("subject_rebinding:manipulated")
            _risk = max(_risk, 1.0)

        if any(pat.search(content) for pat in _confirmation_erosion_pats):
            _flags.append("confirmation_erosion:suspicious")
            _risk = max(_risk, 0.5)

    # Fix 6: Cross-entry escalation aggregation
    _total_cross_esc = 0
    for entry in _entries:
        if entry.get("type", "semantic") not in _identity_types:
            continue
        _cl = entry.get("content", "").lower()
        _total_cross_esc += sum(1 for kw in _escalation_keywords if re.search(r'\b' + re.escape(kw) + r'\b', _cl))
    if _total_cross_esc >= 5 and not any("authority_expansion:manipulated" in f for f in _flags):
        _flags.append("cross_entry_escalation:manipulated")
        _risk = max(_risk, 1.0)
    elif _total_cross_esc >= 3 and not any("authority_expansion" in f for f in _flags):
        _flags.append("cross_entry_escalation:suspicious")
        _risk = max(_risk, 0.5)

    # PATTERN 2 — Permission lattice violation
    _perm_levels = {"read_only": 0, "read-only": 0, "annotate": 1, "recommend": 2,
                    "modify": 3, "approve": 4, "execute": 5, "admin": 6}
    _negation_markers = {"no", "not", "never", "denied", "denial", "excluded", "excluding",
                         "blocked", "restricted", "cannot", "without", "revoked", "prohibited"}
    def _keyword_in_non_negated_context(text, keyword):
        """Check if keyword appears in text without a negation marker nearby in the same sentence.

        Checks both preceding (5 tokens before) and following (5 tokens after) the keyword,
        and also checks for negation markers with punctuation attached (e.g., 'denied:').
        """
        for sentence in re.split(r'[.!?\n]', text):
            if keyword not in sentence:
                continue
            tokens = sentence.split()
            for i, tok in enumerate(tokens):
                if keyword in tok:
                    # Check preceding 5 tokens
                    preceding = {re.sub(r'[^a-z]', '', t) for t in tokens[max(0, i - 5):i]}
                    # Check following 5 tokens
                    following = {re.sub(r'[^a-z]', '', t) for t in tokens[i + 1:i + 6]}
                    nearby = preceding | following
                    if not nearby & _negation_markers:
                        return True
        return False

    _high_severity_pats = [re.compile(r'\b' + kw + r'\b') for kw in ("execute", "approve", "delete", "transfer", "admin")]
    for entry in _entries:
        content = entry.get("content", "").lower()
        for perm, level in _perm_levels.items():
            if perm in content and level <= 1:  # Claims low permission
                # Check if any high-severity keyword appears as whole word in non-negated context
                if any(_keyword_in_non_negated_context(content, m.group())
                       for pat in _high_severity_pats for m in pat.finditer(content)):
                    _flags.append("permission_lattice_violation:suspicious")
                    _risk = max(_risk, 0.6)
                    break

    # PATTERN 3 — Path drift accumulation
    _id_entries = [e for e in _entries if e.get("type", "semantic") in _identity_types]
    if len(_id_entries) >= 3:
        ds_vals = [e.get("downstream_count", 0) for e in _id_entries]
        _increasing = all(ds_vals[i] < ds_vals[i+1] for i in range(len(ds_vals)-1))
        _has_escalation = any("authority_expansion" in f for f in _flags)
        if _increasing and _has_escalation:
            _flags.append("path_drift_accumulation:manipulated")
            _risk = max(_risk, 1.0)

    # PATTERN 4 — Time-bounded authority replay
    _time_bound_pats = [
        re.compile(r'\b(temporary|emergency|30 minutes|this session|incident|override|valid until|expires)\b', re.IGNORECASE),
    ]
    for entry in _entries:
        if entry.get("type", "semantic") not in _identity_types:
            continue
        content = entry.get("content", "")
        age = entry.get("timestamp_age_days", 0) or 0
        if age > 0.5 and any(pat.search(content) for pat in _time_bound_pats):
            _flags.append("time_bounded_replay:suspicious")
            _risk = max(_risk, 0.5)

    # Determine drift level
    if any("manipulated" in f for f in _flags):
        _drift = "MANIPULATED"
    elif _flags:
        _drift = "SUSPICIOUS"
    else:
        _drift = "CLEAN"

    return {
        "identity_drift": _drift,
        "identity_drift_flags": _flags,
        "authority_expansion_score": round(_risk, 2),
    }


def _check_consensus_collapse(memory_state: list, _preprocessed: list = None) -> dict:
    """Detect silent consensus collapse — amplification mistaken for corroboration."""
    _flags = []
    _risk = 0.0
    _entries = _preprocessed if _preprocessed else _preprocess_entries(memory_state)

    n = len(_entries)
    if n < 3:
        return {"consensus_collapse": "CLEAN", "consensus_collapse_flags": [],
                "collapse_ratio": 0.0, "independent_root_estimate": n}

    # Use preprocessed tokens if available, otherwise compute
    all_tokens = [e.get("tokens") or set(w for w in e.get("content", "").lower().split() if len(w) >= 4) for e in _entries]

    # Check for embeddings — use cosine similarity if all entries have them
    _embeddings = [e.get("prompt_embedding") for e in _entries]
    _use_embeddings = all(emb and isinstance(emb, list) and len(emb) > 0 for emb in _embeddings)
    _detection_method = "embedding" if _use_embeddings else "jaccard"

    def _sim(i, j):
        """Compute similarity between entries i and j."""
        if _use_embeddings:
            a, b = _embeddings[i], _embeddings[j]
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(x * x for x in b))
            return dot / (na * nb) if na > 0 and nb > 0 else 0.0
        else:
            if not all_tokens[i] or not all_tokens[j]:
                return 0.0
            inter = len(all_tokens[i] & all_tokens[j])
            uni = len(all_tokens[i] | all_tokens[j])
            return inter / uni if uni > 0 else 0.0

    _sim_threshold = 0.85 if _use_embeddings else 0.3

    # PATTERN 1 — Collapse Ratio
    _similar_groups = set()
    for i in range(n):
        for j in range(i + 1, n):
            if _sim(i, j) >= _sim_threshold:
                _similar_groups.add(i)
                _similar_groups.add(j)

    n_similar = max(len(_similar_groups), 1)

    # Count independent roots via content clusters
    _content_clusters = []
    for i in range(n):
        placed = False
        for ci, cluster in enumerate(_content_clusters):
            rep = cluster[0]
            if _sim(i, rep) >= _sim_threshold:
                cluster.append(i)
                placed = True
                break
        if not placed:
            _content_clusters.append([i])
    independent_roots = max(len(_content_clusters), 1)

    collapse_ratio = round(n_similar / independent_roots, 2) if independent_roots > 0 else 0.0

    if collapse_ratio >= 5.0:
        _flags.append("collapse_ratio:manipulated")
        _risk = max(_risk, 1.0)
    elif collapse_ratio >= 3.0:
        _flags.append("collapse_ratio:suspicious")
        _risk = max(_risk, 0.6)

    # PATTERN 2 — Uncertainty hardening (hedge marker decay)
    _hedge_words = {"likely", "appears", "possibly", "probably", "may", "might",
                    "seems", "approximately", "estimated", "reportedly", "allegedly", "assumed"}

    sorted_entries = sorted(_entries, key=lambda e: e.get("downstream_count", 0))
    hedge_present = []
    for e in sorted_entries:
        words = set(e.get("content", "").lower().split())
        hedge_present.append(bool(words & _hedge_words))

    if n >= 3 and any(hedge_present[:n//2 + 1]) and not any(hedge_present[n//2 + 1:]):
        # Early entries have hedges, later entries don't
        _flags.append("uncertainty_hardening:suspicious")
        _risk = max(_risk, 0.5)

    # Also: no hedges anywhere + strong claims + high downstream
    if not any(hedge_present):
        max_ds = max(e.get("downstream_count", 0) for e in _entries)
        if max_ds > 8 and n_similar >= 3:
            _flags.append("hedge_absent_high_propagation:suspicious")
            _risk = max(_risk, 0.4)

    # PATTERN 3 — Self-reinforcing consensus ("too clean")
    _all_low_conflict = all(e.get("source_conflict", 0) < 0.05 for e in _entries)
    _all_high_trust = all(e.get("source_trust", 0) > 0.85 for e in _entries)
    _all_propagated = all(e.get("downstream_count", 0) > 5 for e in _entries)
    _max_ds_all = max(e.get("downstream_count", 0) for e in _entries)

    if _all_low_conflict and _all_high_trust and _all_propagated and n_similar >= 3:
        if _max_ds_all > 15:
            _flags.append("self_reinforcing:manipulated")
            _risk = max(_risk, 1.0)
        else:
            _flags.append("self_reinforcing:suspicious")
            _risk = max(_risk, 0.5)

    # PATTERN 4 — Confidence recycling loop
    _recycling_pats = re.compile(
        r'\b(confirmed|validated|verified|approved|already reviewed|previously confirmed|on file|prior review|consensus reached)\b',
        re.IGNORECASE)
    for entry in _entries:
        content = entry.get("content", "")
        conflict = entry.get("source_conflict", 0)
        ds = entry.get("downstream_count", 0)
        if _recycling_pats.search(content) and conflict < 0.03 and ds > 6:
            _flags.append("confidence_recycling:suspicious")
            _risk = max(_risk, 0.5)
            break  # One detection suffices

    # PATTERN 5 — Federation Provenance Asymmetry
    if n >= 3:
        _federated = []
        _local = []
        for _ei, _e in enumerate(_entries):
            _pc = _e.get("provenance_chain") or []
            if len(_pc) >= 2:
                _federated.append((_ei, _e))
            else:
                _local.append((_ei, _e))

        if _federated and _local:
            _fed_avg_ds = sum(e.get("downstream_count", 0) for _, e in _federated) / len(_federated)
            _loc_avg_ds = sum(e.get("downstream_count", 0) for _, e in _local) / len(_local) if _local else 1
            _ds_ratio = _fed_avg_ds / max(_loc_avg_ds, 0.5)

            # Topical distinctness
            _max_fed_local_jaccard = 0.0
            for _fi, _fe in _federated:
                for _li, _le in _local:
                    _jfl = _sim(_fi, _li) if _detection_method == "embedding" else (
                        len(all_tokens[_fi] & all_tokens[_li]) / max(len(all_tokens[_fi] | all_tokens[_li]), 1)
                    )
                    _max_fed_local_jaccard = max(_max_fed_local_jaccard, _jfl)

            _topically_distinct = _max_fed_local_jaccard < 0.1
            _ds_amplified = _ds_ratio > 1.8

            if _topically_distinct and _ds_amplified:
                _flags.append("federation_provenance_asymmetry:suspicious")
                _risk = max(_risk, 0.5)
                if _ds_ratio > 3.0 or len(_federated) >= len(_local):
                    _flags.append("federation_provenance_asymmetry:manipulated")
                    _risk = max(_risk, 1.0)
            elif _topically_distinct and len(_local) >= 2:
                _local_self_sim = 0.0
                if len(_local) >= 2:
                    for _la in range(len(_local)):
                        for _lb in range(_la + 1, len(_local)):
                            _lsim = _sim(_local[_la][0], _local[_lb][0]) if _detection_method == "embedding" else (
                                len(all_tokens[_local[_la][0]] & all_tokens[_local[_lb][0]]) / max(len(all_tokens[_local[_la][0]] | all_tokens[_local[_lb][0]]), 1)
                            )
                            _local_self_sim = max(_local_self_sim, _lsim)
                if _local_self_sim > 0.05 or len(_federated) >= 2:
                    _flags.append("federation_topic_injection:suspicious")
                    _risk = max(_risk, 0.5)

    # Capture initial result before genuine corroboration may clear it
    _initial_collapse = "MANIPULATED" if any("manipulated" in f for f in _flags) else ("SUSPICIOUS" if _flags else "CLEAN")

    # Feature 5: Pre-compute content independence
    _max_jaccard = 0.0
    if n >= 3:
        for _ci in range(n):
            for _cj in range(_ci + 1, n):
                _ti, _tj = all_tokens[_ci], all_tokens[_cj]
                if _ti and _tj:
                    _jac = len(_ti & _tj) / len(_ti | _tj) if len(_ti | _tj) > 0 else 0
                    _max_jaccard = max(_max_jaccard, _jac)

    # Genuine consensus check — independent sources with natural variance
    _genuine = False
    if _flags and n >= 3:
        _conflicts = [e.get("source_conflict", 0) for e in _entries]
        _conflict_var = sum((c - sum(_conflicts)/n)**2 for c in _conflicts) / n if n > 0 else 0
        _chains = [tuple(e.get("provenance_chain") or []) for e in _entries]
        _nonempty_chains = [c for c in _chains if len(c) > 0]
        _diverse_chains = len(set(_nonempty_chains)) == len(_nonempty_chains) and len(_nonempty_chains) >= 2
        _has_any_chain = len(_nonempty_chains) >= 1
        _content_independent = (1.0 - _max_jaccard) >= 0.3
        _has_fed_asymmetry = any("federation_" in f for f in _flags)
        _already_manipulated = any("manipulated" in f for f in _flags)
        if (_diverse_chains or (_conflict_var > 0.0001 and _has_any_chain)) and _content_independent and not _has_fed_asymmetry and not _already_manipulated:
            _genuine = True
            _flags = []
            _risk = 0.0

    # Determine collapse level
    if any("manipulated" in f for f in _flags):
        _collapse = "MANIPULATED"
    elif _flags:
        _collapse = "SUSPICIOUS"
    else:
        _collapse = "CLEAN"

    return {
        "consensus_collapse": _collapse,
        "consensus_collapse_flags": _flags,
        "genuine_corroboration": _genuine,
        "consensus_collapse_initial": _initial_collapse,
        "genuine_corroboration_applied": _genuine and _initial_collapse != "CLEAN",
        "collapse_ratio": collapse_ratio,
        "independent_root_estimate": independent_roots,
        "consensus_detection_method": _detection_method,
        "content_independence_score": round(1.0 - _max_jaccard, 2) if n >= 3 else None,
        "content_too_similar": (1.0 - _max_jaccard) < 0.3 if n >= 3 else False,
    }


def _check_provenance_chain(memory_state: list, redis_enabled: bool = False, rget=None, _preprocessed: list = None) -> dict:
    """Detect provenance chain attacks — circular refs, length mismatches, compromised agents."""
    _entries = _preprocessed if _preprocessed else _preprocess_entries(memory_state)

    _flags = []
    _chains = [e.get("provenance_chain") or [] for e in _entries]
    _has_chains = any(len(c) > 0 for c in _chains)
    _max_depth = max((len(c) for c in _chains), default=0)

    if not _has_chains:
        return {"provenance_chain_integrity": "CLEAN", "provenance_chain_flags": [], "chain_depth": 0,
                "pa_signals": {"max_single_hop_jump": 0.0, "origin_mismatch_ratio": 0.0,
                               "echo_ratio": 1.0, "trust_endpoint_delta": 0.0},
                "pa_primary_gate": False, "pa_supplementary_count": 0}

    # PATTERN 1 — Chain length vs downstream mismatch
    for i, e in enumerate(_entries):
        chain = _chains[i]
        if len(chain) > 0 and len(chain) < 2 and e.get("downstream_count", 0) > 8:
            _flags.append("chain_length_mismatch:suspicious")
            break

    # PATTERN 2 — Circular reference
    for chain in _chains:
        if len(chain) != len(set(chain)):
            _flags.append("circular_reference:manipulated")
            break

    # PATTERN 3 — Known compromised agents
    if redis_enabled and rget:
        _compromised = rget("compromised_agents", [])
        if isinstance(_compromised, list) and _compromised:
            _compromised_set = set(_compromised)
            for chain in _chains:
                if _compromised_set & set(chain):
                    _flags.append("compromised_agent:manipulated")
                    break

    # PATTERN 4 — Chain growth anomaly (identical chains)
    _nonempty = [tuple(c) for c in _chains if len(c) > 0]
    if len(_nonempty) >= 3 and len(set(_nonempty)) == 1:
        _flags.append("identical_chains:suspicious")

    # ---- Round 12 PA detector: provenance asymmetry signals ----
    # Filter to entries with provenance_chain length >= 1. Single-hop entries are
    # included because the trust delta from length=1 to length=2 is itself a real
    # provenance hop that can indicate manipulation.

    _pa_primary_gate = False
    _pa_supplementary_count = 0
    _pa_signals = {}

    # Sort entries by chain length for trust evolution analysis
    _entries_by_chain_len = sorted(
        [(len(e.get("provenance_chain") or []), e) for e in _entries],
        key=lambda x: x[0]
    )
    _multi_hop_entries = [(cl, e) for cl, e in _entries_by_chain_len if cl >= 1]

    # PA SIGNAL 1: max_single_hop_jump — trust delta between consecutive chain lengths
    # Compares source_trust of entries at chain_length N vs chain_length N+1
    _max_hop_jump = 0.0
    if len(_multi_hop_entries) >= 2:
        for i in range(len(_multi_hop_entries) - 1):
            t_curr = _multi_hop_entries[i][1].get("source_trust", 0.5)
            t_next = _multi_hop_entries[i + 1][1].get("source_trust", 0.5)
            _max_hop_jump = max(_max_hop_jump, abs(t_next - t_curr))
    _pa_signals["max_single_hop_jump"] = round(_max_hop_jump, 4)

    if _max_hop_jump > 0.07:
        _pa_primary_gate = True

    # PA SIGNAL 2: origin_mismatch_ratio — declared_origin vs actual_origin
    # Checks both corpus format (source.declared_origin) and API format (source_declared_origin)
    _origin_total = 0
    _origin_mismatches = 0
    for e in _entries:
        _decl = e.get("source_declared_origin")
        _actual = e.get("source_actual_origin")
        if not _decl or not _actual:
            src = e.get("source")
            if isinstance(src, dict):
                _decl = _decl or src.get("declared_origin")
                _actual = _actual or src.get("actual_origin")
        if _decl and _actual:
            _origin_total += 1
            if _decl != _actual:
                _origin_mismatches += 1
    _origin_ratio = round(_origin_mismatches / max(_origin_total, 1), 4)
    _pa_signals["origin_mismatch_ratio"] = _origin_ratio
    if _origin_ratio > 0:
        _pa_supplementary_count += 1
        _flags.append("provenance_origin_mismatch:suspicious")

    # PA SIGNAL 3: echo_ratio — unique actual_origins / unique declared_origins
    # Checks both corpus format (source.declared_origin) and API format (source_declared_origin)
    _declared_origins = set()
    _actual_origins = set()
    for e in _entries:
        _decl = e.get("source_declared_origin")
        _actual = e.get("source_actual_origin")
        src = e.get("source")
        if isinstance(src, dict):
            _decl = _decl or src.get("declared_origin")
            _actual = _actual or src.get("actual_origin")
        if _decl:
            _declared_origins.add(_decl)
        if _actual:
            _actual_origins.add(_actual)
    _echo_ratio = round(len(_actual_origins) / max(len(_declared_origins), 1), 4) if _declared_origins else 1.0
    _pa_signals["echo_ratio"] = _echo_ratio
    if _echo_ratio < 1.0:
        _pa_supplementary_count += 1
        _flags.append("echo_amplification:suspicious")

    # PA SIGNAL 4: trust_endpoint_delta — first-hop vs last-hop trust
    _trust_endpoint_delta = 0.0
    if len(_multi_hop_entries) >= 2:
        _trust_first = _multi_hop_entries[0][1].get("source_trust", 0.5)
        _trust_last = _multi_hop_entries[-1][1].get("source_trust", 0.5)
        _trust_endpoint_delta = round(abs(_trust_last - _trust_first), 4)
    _pa_signals["trust_endpoint_delta"] = _trust_endpoint_delta
    if _trust_endpoint_delta > 0.1:
        _pa_supplementary_count += 1
        _flags.append("trust_evolution_anomaly:suspicious")

    # PA classification: primary gate + supplementary → severity
    if _pa_primary_gate and _pa_supplementary_count >= 1:
        _flags.append("provenance_asymmetry:manipulated")
    elif _pa_primary_gate:
        _flags.append("provenance_asymmetry:suspicious")
    elif _pa_supplementary_count >= 2:
        # Multiple supplementary signals without primary — still suspicious
        _flags.append("provenance_asymmetry:suspicious")

    # Final integrity classification (existing + PA signals)
    if any("manipulated" in f for f in _flags):
        _integrity = "MANIPULATED"
    elif _flags:
        _integrity = "SUSPICIOUS"
    else:
        _integrity = "CLEAN"

    return {
        "provenance_chain_integrity": _integrity,
        "provenance_chain_flags": _flags,
        "chain_depth": _max_depth,
        "pa_signals": _pa_signals,
        "pa_primary_gate": _pa_primary_gate,
        "pa_supplementary_count": _pa_supplementary_count,
    }


def _check_sync_bleed(memory_state: list, _preprocessed: list = None) -> dict:
    """Detect partial-sync bleed attacks via sync_version/sync_state fields.

    Requires MemCube v4 fields: sync_version, sync_state, sync_source_id.
    Returns CLEAN immediately if no entries have sync fields (backward compatible).
    """
    _entries = _preprocessed if _preprocessed else _preprocess_entries(memory_state)
    _flags = []

    # Graceful degradation: if no entries have sync fields, return CLEAN
    _has_sync = any(e.get("sync_version") or e.get("sync_state") for e in _entries)
    if not _has_sync:
        return {"sync_bleed": "CLEAN", "sync_bleed_flags": [],
                "sync_signals": {"stale_fraction": 0, "pending_fraction": 0,
                                 "version_count": 0, "cross_version_jaccard": 1.0,
                                 "stale_outnumbers_fresh": False}}

    n = len(_entries)

    # Signal A: stale_fraction
    _stale = sum(1 for e in _entries if e.get("sync_state") == "stale")
    _pending = sum(1 for e in _entries if e.get("sync_state") == "pending")
    _current = sum(1 for e in _entries if e.get("sync_state") == "current")
    _stale_fraction = round((_stale + _pending) / max(n, 1), 4)
    _pending_fraction = round(_pending / max(n, 1), 4)

    # Signal B: version_count
    _versions = set(e.get("sync_version") for e in _entries if e.get("sync_version"))
    _version_count = len(_versions)

    # Signal C: stale_outnumbers_fresh
    _stale_outnumbers = (_stale + _pending) > _current

    # Signal D: cross_version_jaccard — content similarity between entries of different versions
    _cross_jaccard = 1.0
    if _version_count >= 2:
        # Group entries by version
        _by_version = {}
        for e in _entries:
            v = e.get("sync_version", "unknown")
            if v not in _by_version:
                _by_version[v] = []
            _by_version[v].append(e)

        # Compute Jaccard between each pair of version groups
        _version_list = list(_by_version.keys())
        _min_jaccard = 1.0
        for i in range(len(_version_list)):
            for j in range(i + 1, len(_version_list)):
                # Pool content tokens from each version group
                _tokens_i = set()
                for e in _by_version[_version_list[i]]:
                    _tokens_i.update(w.lower() for w in e.get("content", "").split() if len(w) >= 4 and w.lower() not in _STOPWORDS)
                _tokens_j = set()
                for e in _by_version[_version_list[j]]:
                    _tokens_j.update(w.lower() for w in e.get("content", "").split() if len(w) >= 4 and w.lower() not in _STOPWORDS)
                if _tokens_i and _tokens_j:
                    _jac = len(_tokens_i & _tokens_j) / len(_tokens_i | _tokens_j)
                    _min_jaccard = min(_min_jaccard, _jac)
        _cross_jaccard = round(_min_jaccard, 4)

    _signals = {
        "stale_fraction": _stale_fraction,
        "pending_fraction": _pending_fraction,
        "version_count": _version_count,
        "cross_version_jaccard": _cross_jaccard,
        "stale_outnumbers_fresh": _stale_outnumbers,
    }

    # Classification — requires stale presence as hard gate to avoid FP on
    # latency-only controls where content differs by topic, not by contradiction.
    if _stale_outnumbers and _cross_jaccard < 0.15:
        _flags.append("sync_bleed:manipulated")
    elif _stale_outnumbers and _cross_jaccard < 0.25:
        _flags.append("sync_bleed:suspicious")
    elif _stale_fraction >= 0.4 and _cross_jaccard < 0.15:
        # Near-equal stale split with strong content contradiction
        _flags.append("sync_bleed:suspicious")

    if any("manipulated" in f for f in _flags):
        _level = "MANIPULATED"
    elif _flags:
        _level = "SUSPICIOUS"
    else:
        _level = "CLEAN"

    return {"sync_bleed": _level, "sync_bleed_flags": _flags, "sync_signals": _signals}


def _check_confidence_calibration(memory_state: list, _preprocessed: list = None) -> dict:
    """Detect confidence calibration attacks — overconfident stale memories.

    Requires MemCube v4 field: model_confidence (optional).
    Signals operate on entry-level age, trust, and type-specific Weibull half-lives.
    Returns CLEAN if no actionable signals detected.
    """
    _entries = _preprocessed if _preprocessed else _preprocess_entries(memory_state)
    _flags = []
    n = len(_entries)
    if n < 2:
        return {"confidence_calibration": "CLEAN", "cc_flags": [], "cc_signals": {
            "correlated_consensus": False, "stale_but_confident_count": 0,
            "age_cluster_detected": False, "model_confidence_divergence": False,
            "age_mean": 0.0, "age_std": 0.0, "trust_std": 0.0}}

    # Weibull half-lives per memory type
    _HALFLIFE = {"tool_state": 5, "shared_workflow": 9, "episodic": 14,
                 "preference": 23, "semantic": 69, "policy": 139, "identity": 347}

    ages = [e.get("timestamp_age_days", 0) for e in _entries]
    trusts = [e.get("source_trust", 0.5) for e in _entries]
    conflicts = [e.get("source_conflict", 0) for e in _entries]
    age_mean = sum(ages) / n
    age_std = (sum((a - age_mean) ** 2 for a in ages) / n) ** 0.5
    trust_mean = sum(trusts) / n
    trust_std = (sum((t - trust_mean) ** 2 for t in trusts) / n) ** 0.5

    # Signal 1: correlated_consensus — similar ages + similar trust + low conflict
    _correlated = age_std < 5 and trust_std < 0.1 and max(conflicts) < 0.2

    # Signal 2: stale_but_confident — entries past type-specific Weibull half-life with high trust
    _sbc_count = 0
    for e in _entries:
        hl = _HALFLIFE.get(e.get("type", "semantic"), 69)
        if e.get("timestamp_age_days", 0) > hl and e.get("source_trust", 0) > 0.8:
            _sbc_count += 1

    # Signal 3: age_cluster — 3+ entries within narrow age window, all > 10 days
    _age_cluster = False
    if n >= 3:
        age_range = max(ages) - min(ages)
        _age_cluster = age_range < 5 and min(ages) > 10

    # Signal 4: model_confidence divergence — high confidence on aging entries
    _mc_divergence = False
    _mc_values = [e.get("model_confidence") for e in _entries if e.get("model_confidence") is not None]
    if _mc_values:
        mc_max = max(_mc_values)
        avg_hl = sum(_HALFLIFE.get(e.get("type", "semantic"), 69) for e in _entries) / n
        age_ratio = age_mean / max(avg_hl, 1)
        _mc_divergence = mc_max > 0.8 and age_ratio > 0.3

    _signals = {
        "correlated_consensus": _correlated,
        "stale_but_confident_count": _sbc_count,
        "age_cluster_detected": _age_cluster,
        "model_confidence_divergence": _mc_divergence,
        "age_mean": round(age_mean, 2),
        "age_std": round(age_std, 2),
        "trust_std": round(trust_std, 4),
    }

    # Classification
    if (_correlated or _age_cluster) and _sbc_count >= 2:
        _flags.append("confidence_calibration:manipulated")
    elif _mc_divergence and _sbc_count >= 2:
        _flags.append("confidence_calibration:manipulated")
    elif _mc_divergence and _sbc_count == 1:
        # Single stale-but-confident entry + mc divergence → suspicious (not manipulated)
        _flags.append("confidence_calibration:suspicious")
    elif _mc_divergence:
        _flags.append("confidence_calibration:suspicious")
    elif _correlated and _sbc_count >= 1:
        _flags.append("confidence_calibration:suspicious")
    elif _age_cluster:
        _flags.append("confidence_calibration:suspicious")
    elif _sbc_count >= 1:
        _flags.append("confidence_calibration:suspicious")

    if any("manipulated" in f for f in _flags):
        _level = "MANIPULATED"
    elif _flags:
        _level = "SUSPICIOUS"
    else:
        _level = "CLEAN"

    return {"confidence_calibration": _level, "cc_flags": _flags, "cc_signals": _signals}


def _check_naturalness(memory_state: list, action_type: str = "reversible", _preprocessed: list = None, domain: str = "general") -> dict:
    """Detect synthetic/fabricated memory states via statistical naturalness signals."""
    _entries = _preprocessed if _preprocessed else _preprocess_entries(memory_state)

    _flags = []
    _score = 1.0
    n = len(_entries)

    # SIGNAL 1 — Trust variance
    if n >= 3:
        trusts = [e.get("source_trust", 0.5) for e in _entries]
        mean_t = sum(trusts) / n
        var_t = sum((t - mean_t) ** 2 for t in trusts) / n
        if var_t == 0.0 or (var_t < 0.00001 and n >= 3):
            _flags.append("uniform_trust")
            _score -= 0.2

    # SIGNAL 2 — Conflict uniformity
    if n >= 3:
        if all(e.get("source_conflict", 0) < 0.02 for e in _entries):
            _flags.append("zero_conflict")
            _score -= 0.2

    # SIGNAL 3 — Downstream implausibility
    for e in _entries:
        if e.get("downstream_count", 0) > 10 and e.get("timestamp_age_days", 0) < 0.1:
            _flags.append("downstream_implausible")
            _score -= 0.2
            break

    # SIGNAL 4 — Age distribution
    if n >= 3 and all(e.get("timestamp_age_days", 0) == 0 for e in _entries):
        if action_type in ("irreversible", "destructive"):
            _flags.append("all_zero_age")
            _score -= 0.2

    # SIGNAL 5 — Perfect trust scores
    if any(e.get("source_trust", 0) == 1.0 for e in _entries):
        _flags.append("perfect_trust")
        _score -= 0.2

    _score = round(max(0.0, _score), 2)

    if _score >= 0.8:
        _level = "ORGANIC"
    elif _score >= 0.6:
        _level = "PLAUSIBLE"
    elif _score >= 0.4:
        _level = "SYNTHETIC"
    else:
        _level = "FABRICATED"

    _baseline = "strict" if domain in ("fintech", "medical", "legal") else ("loose" if domain == "customer_support" else "standard")
    return {"naturalness_score": _score, "naturalness_level": _level, "naturalness_flags": _flags,
            "domain_naturalness_baseline": _baseline}


def _extract_attack_signature(memory_state: list, detection_results: dict, domain: str, content_hash: str = None) -> dict:
    """Extract vaccine signature from a blocked attack for fleet-wide immunity."""
    _entries = []
    for e in memory_state:
        if isinstance(e, dict):
            _entries.append(e)
        else:
            _entries.append({"content": getattr(e, "content", ""), "downstream_count": getattr(e, "downstream_count", 0),
                "source_trust": getattr(e, "source_trust", 0.5)})

    if not content_hash:
        content_hash = hashlib.sha256(_entries[0].get("content", "").encode()).hexdigest()[:16] if _entries else ""
    max_ds = max((e.get("downstream_count", 0) for e in _entries), default=0)
    trusts = [e.get("source_trust", 0.5) for e in _entries]
    mean_t = sum(trusts) / max(len(trusts), 1)
    var_t = sum((t - mean_t) ** 2 for t in trusts) / max(len(trusts), 1)

    attack_type = "unknown"
    if detection_results.get("timestamp_integrity") == "MANIPULATED":
        attack_type = "timestamp_manipulation"
    elif detection_results.get("identity_drift") == "MANIPULATED":
        attack_type = "identity_drift"
    elif detection_results.get("consensus_collapse") == "MANIPULATED":
        attack_type = "consensus_collapse"

    return {
        "signature_id": str(uuid.uuid4()),
        "created_at": _time.time(),
        "attack_type": attack_type,
        "content_hash_prefix": content_hash,
        "downstream_pattern": "high" if max_ds > 10 else "low",
        "trust_range": "uniform" if var_t < 0.005 else "varied",
        "domain": domain,
        "ttl_days": 30,
    }


def _compute_attack_surface_score(ts_result: dict, id_result: dict, cc_result: dict, pc_result: dict = None,
                                   sb_result: dict = None, cc_calibration_result: dict = None) -> dict:
    """Compute compound attack surface score from detection layers."""
    _RISK = {"CLEAN": 0.0, "VALID": 0.0, "SUSPICIOUS": 0.5, "MANIPULATED": 1.0}
    _pc_risk = _RISK.get((pc_result or {}).get("provenance_chain_integrity", "CLEAN"), 0.0)
    _sb_risk = _RISK.get((sb_result or {}).get("sync_bleed", "CLEAN"), 0.0)
    _cc_cal_risk = _RISK.get((cc_calibration_result or {}).get("confidence_calibration", "CLEAN"), 0.0)
    risks = sorted([
        _RISK.get(ts_result.get("timestamp_integrity", "VALID"), 0.0),
        _RISK.get(id_result.get("identity_drift", "CLEAN"), 0.0),
        _RISK.get(cc_result.get("consensus_collapse", "CLEAN"), 0.0),
        _pc_risk,
        _sb_risk,
        _cc_cal_risk,
    ], reverse=True)

    score = round(risks[0] + 0.3 * risks[1] + 0.1 * risks[2] + 0.05 * risks[3], 2)

    if score == 0.0:
        level = "NONE"
    elif score < 0.50:
        level = "LOW"
    elif score < 0.70:
        level = "MODERATE"
    elif score < 1.00:
        level = "HIGH"
    else:
        level = "CRITICAL"

    active = []
    if _RISK.get(ts_result.get("timestamp_integrity", "VALID"), 0.0) > 0:
        active.append("timestamp_integrity")
    if _RISK.get(id_result.get("identity_drift", "CLEAN"), 0.0) > 0:
        active.append("identity_drift")
    if _RISK.get(cc_result.get("consensus_collapse", "CLEAN"), 0.0) > 0:
        active.append("consensus_collapse")
    if _pc_risk > 0:
        active.append("provenance_chain")
    if _sb_risk > 0:
        active.append("sync_bleed")
    if _cc_cal_risk > 0:
        active.append("confidence_calibration")

    return {"attack_surface_score": score, "attack_surface_level": level, "active_detection_layers": active}
