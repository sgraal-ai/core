# Sgraal Architecture

Technical architecture of the Sgraal memory governance protocol.

---

## Ω_MEM Scoring Formula

The core scoring engine computes a single risk score **Ω_MEM** (0–100) from weighted components:

```
Ω_MEM = Σ βᵢ · Cᵢ(x) × C_action × C_domain
```

Where:
- `βᵢ` — proprietary weights per component
- `Cᵢ(x)` — individual component scores (0–100, higher = more risk)
- `C_action` — multiplier based on action reversibility
- `C_domain` — multiplier based on domain criticality

### Scoring Components

| Component | Measures | Method | Example |
|-----------|----------|--------|---------|
| **s_freshness** | How stale is the memory? | Weibull decay function, type-specific λ | tool_state at 30 days → 98.9/100 |
| **s_drift** | Has the memory drifted from its original meaning? | Weighted blend of freshness + interference | High freshness + high conflict → elevated drift |
| **s_provenance** | How trusted is the memory source? | Inverse of source_trust (0–1 → 100–0) | source_trust=0.5 → provenance=50/100 |
| **s_propagation** | Blast radius if memory is wrong | Scaled downstream_count | 8 downstream decisions → 64/100 |
| **r_recall** | Likelihood of accurate recall | Blend of freshness + provenance | Stale + untrusted → high recall risk |
| **r_encode** | Quality of original encoding | Function of provenance | Low trust source → encoding risk |
| **s_interference** | Conflict between sources | Dempster-Shafer K coefficient (0–1 → 0–100) | K=0.7 → 70/100 interference |
| **s_recovery** | Ability to recover from errors | Inverse of freshness | Fresh memory → high recovery potential |
| **r_belief** | Model belief divergence | Divergence between outputs with/without entry | r_belief=0.1 → 90/100 risk |
| **s_relevance** | Intent-drift from current goal | Cosine similarity between embeddings | sim<0.6 → +20 penalty per entry |

Optional opt-in components:
| Component | Measures | Method |
|-----------|----------|--------|
| **r_importance** | PageRank authority in dependency graph | PR(v) = (1-d)/N + d·Σ PR(u)/L(u) |

---

## Decision Thresholds

| Ω_MEM Range | Decision | Meaning |
|-------------|----------|---------|
| 0 – 24 | **USE_MEMORY** | Memory is reliable. Proceed. |
| 25 – 44 | **WARN** | Some risk detected. Log and monitor. |
| 45 – 69 | **ASK_USER** | Elevated risk. Seek human confirmation. |
| 70 – 100 | **BLOCK** | Unsafe to act. Stop and verify. |

Thresholds are configurable per request via the `thresholds` field.

---

## Multipliers

### C_action — Action Reversibility

Scales risk based on how reversible the action is:

| Category | Effect |
|----------|--------|
| Informational | Lowest multiplier — reading only |
| Reversible | Moderate — action can be undone |
| Irreversible | High — action cannot be reversed |
| Destructive | Highest — permanent damage possible |

### C_domain — Domain Criticality

Scales risk based on the domain's sensitivity:

| Category | Effect |
|----------|--------|
| General | Baseline |
| Customer support | Slightly elevated |
| Coding | Moderate |
| Legal | High |
| Fintech | Very high |
| Medical | Highest — human life at stake |

---

## Memory Types and Decay

Each memory type decays at a different rate, modeled by a **Weibull decay function**:

```
decay(t) = 1 - exp(-(t · λ)^k)
```

Types ordered from fastest to slowest decay:

| Type | Decay Rate | Example |
|------|-----------|---------|
| **tool_state** | Very fast | API responses, tool outputs |
| **shared_workflow** | Fast | Multi-agent workflow state |
| **episodic** | Moderate | Events, conversations |
| **preference** | Slow | User preferences |
| **semantic** | Very slow | General knowledge, facts |
| **policy** | Near-permanent | Rules, constraints |
| **identity** | Almost never | Core identity facts |

A tool_state entry becomes stale in days. An identity entry remains fresh for years.

---

## Self-Healing Loop

When Sgraal detects risk, it generates a **repair plan** — a prioritized list of healing actions:

| Action | Trigger | Effect |
|--------|---------|--------|
| **REFETCH** | Stale memory (freshness > 60) | Re-fetch from original source |
| **VERIFY_WITH_SOURCE** | Source conflict (interference > 50) | Cross-check against authoritative source |
| **REBUILD_WORKING_SET** | Low model belief (r_belief < 0.3) | Reconstruct working memory from scratch |

### Lyapunov Stability Guarantee

The healing loop is provably convergent. We use a **Lyapunov candidate function**:

```
V(x) = ω² / 200
```

With derivative:

```
V̇(x) = -decay_rate × V(x)
```

Since V(x) > 0 for all ω > 0 (positive definite) and V̇(x) < 0 whenever V(x) > 0 (negative definite), **asymptotic stability is guaranteed**: the healing loop always converges toward equilibrium (ω → 0).

Each healing action has a different decay rate — REFETCH converges fastest, REBUILD_WORKING_SET slowest.

---

## Privacy Layer

Three layers of protection for memory content:

### Layer 1 — Entry ID Obfuscation
HMAC-SHA256 hashing of entry IDs with a per-session key. Original IDs never leave the system unless explicitly opted in (`detail_level: "full"`).

### Layer 2 — Reason Abstraction
Detailed repair reasons are mapped to abstract categories:
- STALE, CONFLICT, LOW_TRUST, PROPAGATION_RISK, INTENT_DRIFT

No specific values, ages, or content leak in the default response.

### Layer 3 — Zero-Knowledge Commitment
A SHA256 commitment hash binds the Ω_MEM score to the entry IDs without revealing the entries. Verifiable without disclosure.

### ε-Differential Privacy (Optional)
Laplace noise mechanism guarantees:

```
Pr[M(D) ∈ S] ≤ exp(ε) · Pr[M(D') ∈ S]
```

For adjacent datasets D, D' differing in one memory entry. Configurable ε (smaller = stronger privacy, more noise). Noise is deterministic (seeded) to preserve the A2 axiom.

---

## Formal Guarantees

### Z3 SMT Verification
Healing policies and compliance rules are formally verified using the Z3 theorem prover:
- No two rules produce contradictory actions for the same state
- BLOCK is always reachable when Ω_MEM exceeds threshold
- Healing counter increments are monotonically increasing
- No compliance rule can both allow and block the same action

Falls back to logical verification when Z3 is unavailable.

### A2 Axiom — Determinism
Identical memory state + identical healing counter = identical Ω_MEM score. Always. No randomness in the scoring path. Verified by 100-run stress test.

### Conformal Prediction (Planned)
Future: calibrated prediction intervals for Ω_MEM scores, guaranteeing coverage probability.

---

## Drift Detection Ensemble

Four methods detect memory drift:

| Method | What It Detects |
|--------|----------------|
| **KL Divergence** | Information-theoretic distance between current and baseline distributions |
| **Wasserstein Distance** | Earth Mover's distance — how much "work" to transform one distribution to another |
| **Jensen-Shannon Divergence** | Symmetric, bounded version of KL — JSD(P,Q) = ½·KL(P‖M) + ½·KL(Q‖M) |
| **CUSUM + EWMA** | Sequential change detection — CUSUM for abrupt shifts, EWMA for gradual drift |

The ensemble combines all four with configurable weights. `drift_sustained = true` when CUSUM and EWMA both agree on 4+ consecutive degradations.

---

## Shapley Explainability

Every preflight response includes **Shapley values** — each component's marginal contribution to the final Ω_MEM score.

- Positive Shapley value = component increases risk
- Negative Shapley value = component decreases risk (e.g. s_recovery)
- Values sum to the final Ω_MEM score

This tells agents exactly *why* a decision was made and *which component to fix first* for maximum improvement (see also: Value of Information scoring).

---

## Value of Information (VoI)

For each at-risk memory entry:

```
VoI = E[Ω(act|healed)] - E[Ω(act)]
```

The expected improvement in Ω_MEM if that specific entry were healed. At-risk warnings are sorted by VoI descending — **highest ROI first**. This tells agents which entry to heal for maximum impact.

---

## Compliance Profiles

| Profile | Key Rules |
|---------|-----------|
| **GENERAL** | No additional restrictions |
| **EU_AI_ACT** | Article 12 (logging), Article 9 (medical oversight), Article 13 (transparency) |
| **FDA_510K** | Predicate comparison, risk classification |
| **HIPAA** | PHI integrity guarantee |

Critical violations automatically override the recommended action to BLOCK.

---

## Architecture Diagram

```
Agent → POST /v1/preflight → Scoring Engine → Decision
                                  ↓
                          [10 components scored]
                                  ↓
                     Ω_MEM × C_action × C_domain
                                  ↓
                    ┌─────────────┴──────────────┐
                    ↓              ↓              ↓
              USE_MEMORY         WARN           BLOCK
                    ↓              ↓              ↓
              [proceed]     [log + monitor]   [STOP + heal]
                                                  ↓
                                          Repair Plan Generated
                                                  ↓
                                      POST /v1/heal → Lyapunov ✓
```
